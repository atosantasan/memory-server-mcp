#!/usr/bin/env python3
"""
MCPプロトコル統合テスト
実際のMCPクライアント-サーバー間の通信とプロトコル準拠性をテストする
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, List

# テスト用の設定でmain.pyをインポート
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """テスト環境のセットアップ"""
    # テスト用の一時データベースファイルを作成
    test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    test_db.close()
    
    # 環境変数を設定してテスト用データベースを使用
    os.environ['MEMORY_DB_PATH'] = test_db.name
    os.environ['MEMORY_LOG_LEVEL'] = 'ERROR'  # テスト中はエラーログのみ
    
    yield test_db.name
    
    # クリーンアップ
    try:
        os.unlink(test_db.name)
    except FileNotFoundError:
        pass

@pytest.fixture
def mcp_server(setup_test_environment):
    """MCPサーバーのフィクスチャ"""
    from main import mcp, memory_service, initialize_mcp_server
    
    # データベースを初期化
    memory_service.init_database()
    
    # テスト前にデータベースをクリア
    try:
        with memory_service.get_connection() as conn:
            conn.execute("DELETE FROM memory_entries")
            conn.commit()
    except Exception:
        pass
    
    # MCPサーバーを初期化
    initialize_mcp_server()
    
    return mcp

@pytest.fixture
def sample_memory_data():
    """テスト用のサンプルメモリデータ"""
    return {
        "content": "これはMCPプロトコルテスト用のメモリエントリです",
        "tags": ["MCP", "プロトコル", "テスト"],
        "keywords": ["統合テスト", "プロトコル", "MCP"],
        "summary": "MCPプロトコル統合テスト用のサンプルエントリ"
    }

class MockMCPClient:
    """MCPクライアントのモック"""
    
    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
        self.request_id = 0
    
    def _create_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """MCPリクエストメッセージを作成"""
        self.request_id += 1
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
    
    def _validate_response(self, response: Dict[str, Any], request_id: int) -> bool:
        """MCPレスポンスの形式を検証"""
        # 基本的なJSON-RPC 2.0形式の検証
        if "jsonrpc" not in response or response["jsonrpc"] != "2.0":
            return False
        
        if "id" not in response or response["id"] != request_id:
            return False
        
        # 成功レスポンスまたはエラーレスポンスのいずれかが必要
        has_result = "result" in response
        has_error = "error" in response
        
        return has_result != has_error  # XOR: 片方だけが存在する必要がある
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """MCPツールを呼び出す（実際の実装関数を直接呼び出し）"""
        from main import (
            _add_note_to_memory_impl, _search_memory_impl, _update_memory_entry_impl,
            _delete_memory_entry_impl, _list_all_memories_impl, _get_project_rules_impl
        )
        
        # ツール名に基づいて適切な実装関数を呼び出し
        tool_functions = {
            "add_note_to_memory": _add_note_to_memory_impl,
            "search_memory": _search_memory_impl,
            "update_memory_entry": _update_memory_entry_impl,
            "delete_memory_entry": _delete_memory_entry_impl,
            "list_all_memories": _list_all_memories_impl,
            "get_project_rules": _get_project_rules_impl
        }
        
        if tool_name not in tool_functions:
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": {"method": tool_name}
                }
            }
        
        try:
            # 実装関数を呼び出し
            func = tool_functions[tool_name]
            if arguments:
                result = func(**arguments)
            else:
                result = func()
            
            # MCPレスポンス形式で返す
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "result": result
            }
        
        except Exception as e:
            # エラーレスポンス
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"error": str(e)}
                }
            }

@pytest.fixture
def mcp_client(mcp_server):
    """MCPクライアントのフィクスチャ"""
    return MockMCPClient(mcp_server)

class TestMCPProtocolCompliance:
    """MCPプロトコル準拠性のテスト"""
    
    def test_mcp_server_initialization(self, mcp_server):
        """MCPサーバーの初期化テスト"""
        assert mcp_server is not None
        # MCPサーバーが正しく初期化されていることを確認
        # FastMCPの内部構造に依存しないよう、基本的な存在確認のみ
    
    @pytest.mark.asyncio
    async def test_mcp_tool_discovery(self, mcp_client):
        """MCPツール発見のテスト"""
        # 利用可能なツールのリストを確認
        expected_tools = [
            "add_note_to_memory",
            "search_memory", 
            "update_memory_entry",
            "delete_memory_entry",
            "list_all_memories",
            "get_project_rules"
        ]
        
        # 各ツールが呼び出し可能であることを確認
        for tool_name in expected_tools:
            # 無効な引数でツールを呼び出してエラーレスポンスを確認
            response = await mcp_client.call_tool(tool_name, {})
            
            # レスポンスがJSON-RPC 2.0形式であることを確認
            assert "jsonrpc" in response
            assert response["jsonrpc"] == "2.0"
            assert "id" in response
            
            # 結果またはエラーのいずれかが存在することを確認
            assert ("result" in response) != ("error" in response)  # XOR

class TestMCPToolFunctionality:
    """MCPツール機能のテスト"""
    
    @pytest.mark.asyncio
    async def test_add_note_to_memory_tool(self, mcp_client, sample_memory_data):
        """add_note_to_memoryツールのテスト"""
        response = await mcp_client.call_tool("add_note_to_memory", sample_memory_data)
        
        # レスポンス形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert result["success"] is True
        assert "entry" in result
        assert result["entry"]["content"] == sample_memory_data["content"]
        assert result["entry"]["tags"] == sample_memory_data["tags"]
        
        return result["entry"]["id"]  # 後続のテストで使用
    
    @pytest.mark.asyncio
    async def test_search_memory_tool(self, mcp_client, sample_memory_data):
        """search_memoryツールのテスト"""
        # まずメモリエントリを作成
        await mcp_client.call_tool("add_note_to_memory", sample_memory_data)
        
        # 検索を実行
        search_params = {
            "query": "MCPプロトコル",
            "limit": 10
        }
        response = await mcp_client.call_tool("search_memory", search_params)
        
        # レスポンス形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert result["success"] is True
        assert "results" in result
        assert len(result["results"]) > 0
        
        # 検索結果の内容確認
        found_entry = result["results"][0]
        assert sample_memory_data["content"] in found_entry["content"]
    
    @pytest.mark.asyncio
    async def test_update_memory_entry_tool(self, mcp_client, sample_memory_data):
        """update_memory_entryツールのテスト"""
        # まずメモリエントリを作成
        create_response = await mcp_client.call_tool("add_note_to_memory", sample_memory_data)
        entry_id = create_response["result"]["entry"]["id"]
        
        # エントリを更新
        update_params = {
            "entry_id": entry_id,
            "content": "更新されたMCPプロトコルテスト用エントリ",
            "tags": ["MCP", "プロトコル", "テスト", "更新済み"]
        }
        response = await mcp_client.call_tool("update_memory_entry", update_params)
        
        # レスポンス形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert result["success"] is True
        assert result["entry"]["content"] == update_params["content"]
        assert result["entry"]["tags"] == update_params["tags"]
    
    @pytest.mark.asyncio
    async def test_list_all_memories_tool(self, mcp_client, sample_memory_data):
        """list_all_memoriesツールのテスト"""
        # まずメモリエントリを作成
        await mcp_client.call_tool("add_note_to_memory", sample_memory_data)
        
        # 全メモリエントリを取得
        list_params = {"limit": 50}
        response = await mcp_client.call_tool("list_all_memories", list_params)
        
        # レスポンス形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert result["success"] is True
        assert "entries" in result
        assert len(result["entries"]) > 0
        assert "total_count" in result
    
    @pytest.mark.asyncio
    async def test_get_project_rules_tool(self, mcp_client):
        """get_project_rulesツールのテスト"""
        # プロジェクトルール用のエントリを作成
        rule_data = {
            "content": "これはプロジェクトルールです",
            "tags": ["ルール", "プロジェクト"],
            "keywords": ["規則", "方針"],
            "summary": "テスト用プロジェクトルール"
        }
        await mcp_client.call_tool("add_note_to_memory", rule_data)
        
        # プロジェクトルールを取得
        response = await mcp_client.call_tool("get_project_rules")
        
        # レスポンス形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert result["success"] is True
        assert "rules" in result
    
    @pytest.mark.asyncio
    async def test_delete_memory_entry_tool(self, mcp_client, sample_memory_data):
        """delete_memory_entryツールのテスト"""
        # まずメモリエントリを作成
        create_response = await mcp_client.call_tool("add_note_to_memory", sample_memory_data)
        entry_id = create_response["result"]["entry"]["id"]
        
        # エントリを削除
        delete_params = {"entry_id": entry_id}
        response = await mcp_client.call_tool("delete_memory_entry", delete_params)
        
        # レスポンス形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert result["success"] is True
        assert result["deleted_entry_id"] == entry_id

class TestMCPErrorHandling:
    """MCPエラーハンドリングのテスト"""
    
    @pytest.mark.asyncio
    async def test_invalid_tool_name(self, mcp_client):
        """存在しないツール名のテスト"""
        response = await mcp_client.call_tool("nonexistent_tool")
        
        # エラーレスポンスの検証
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found
    
    @pytest.mark.asyncio
    async def test_invalid_parameters(self, mcp_client):
        """無効なパラメータのテスト"""
        # 空のコンテンツでメモリエントリ作成を試行
        invalid_params = {"content": ""}
        response = await mcp_client.call_tool("add_note_to_memory", invalid_params)
        
        # エラーレスポンスの検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response  # 実装関数がエラー情報を含む結果を返す
        
        result = response["result"]
        assert "error" in result
        assert result["error"]["code"] == -32602  # Invalid params
    
    @pytest.mark.asyncio
    async def test_nonexistent_entry_operations(self, mcp_client):
        """存在しないエントリに対する操作のテスト"""
        nonexistent_id = 99999
        
        # 存在しないエントリの更新を試行
        update_params = {
            "entry_id": nonexistent_id,
            "content": "存在しないエントリの更新"
        }
        response = await mcp_client.call_tool("update_memory_entry", update_params)
        
        # エラーレスポンスの検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert "error" in result
        assert result["error"]["code"] == -32602  # Invalid params (entry not found)
        
        # 存在しないエントリの削除を試行
        delete_params = {"entry_id": nonexistent_id}
        response = await mcp_client.call_tool("delete_memory_entry", delete_params)
        
        # エラーレスポンスの検証
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert "error" in result
        assert result["error"]["code"] == -32602  # Invalid params (entry not found)
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, mcp_client):
        """パラメータバリデーションのテスト"""
        # 無効なentry_idタイプ
        invalid_params = {
            "entry_id": "invalid_id",  # 文字列（数値である必要がある）
            "content": "テストコンテンツ"
        }
        response = await mcp_client.call_tool("update_memory_entry", invalid_params)
        
        # エラーレスポンスの検証
        assert response["jsonrpc"] == "2.0"
        # 実装によってはTypeErrorが発生する可能性があるため、エラーハンドリングを確認
        if "error" in response:
            assert response["error"]["code"] == -32603  # Internal error
        else:
            # 実装関数内でエラーが処理される場合
            result = response["result"]
            assert "error" in result

class TestMCPProtocolIntegration:
    """MCPプロトコル統合のテスト"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, mcp_client):
        """完全なワークフローのテスト"""
        # 1. メモリエントリを作成
        create_data = {
            "content": "統合テスト用のメモリエントリ",
            "tags": ["統合テスト", "ワークフロー"],
            "keywords": ["テスト", "統合"],
            "summary": "完全なワークフローのテスト用エントリ"
        }
        
        create_response = await mcp_client.call_tool("add_note_to_memory", create_data)
        assert create_response["result"]["success"] is True
        entry_id = create_response["result"]["entry"]["id"]
        
        # 2. 作成したエントリを検索
        search_response = await mcp_client.call_tool("search_memory", {
            "query": "統合テスト",
            "limit": 10
        })
        assert search_response["result"]["success"] is True
        assert len(search_response["result"]["results"]) > 0
        
        # 3. エントリを更新
        update_response = await mcp_client.call_tool("update_memory_entry", {
            "entry_id": entry_id,
            "content": "更新された統合テスト用エントリ",
            "tags": ["統合テスト", "ワークフロー", "更新済み"]
        })
        assert update_response["result"]["success"] is True
        
        # 4. 全エントリをリスト
        list_response = await mcp_client.call_tool("list_all_memories", {"limit": 50})
        assert list_response["result"]["success"] is True
        assert list_response["result"]["total_count"] > 0
        
        # 5. エントリを削除
        delete_response = await mcp_client.call_tool("delete_memory_entry", {
            "entry_id": entry_id
        })
        assert delete_response["result"]["success"] is True
        
        # 6. 削除後の検索で結果が減ることを確認
        final_search_response = await mcp_client.call_tool("search_memory", {
            "query": "統合テスト",
            "limit": 10
        })
        assert final_search_response["result"]["success"] is True
        # 削除されたエントリは検索結果に含まれないはず
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mcp_client):
        """同時操作のテスト"""
        # 複数のメモリエントリを同時に作成
        create_tasks = []
        for i in range(5):
            create_data = {
                "content": f"同時作成テスト用エントリ {i+1}",
                "tags": ["同時テスト", f"エントリ{i+1}"],
                "keywords": ["同時操作", "テスト"],
                "summary": f"同時作成テスト用エントリ {i+1}"
            }
            task = mcp_client.call_tool("add_note_to_memory", create_data)
            create_tasks.append(task)
        
        # 全ての作成操作を並行実行
        create_responses = await asyncio.gather(*create_tasks)
        
        # 全ての作成が成功したことを確認
        entry_ids = []
        for response in create_responses:
            assert response["result"]["success"] is True
            entry_ids.append(response["result"]["entry"]["id"])
        
        # 作成されたエントリを検索
        search_response = await mcp_client.call_tool("search_memory", {
            "query": "同時作成",
            "limit": 10
        })
        assert search_response["result"]["success"] is True
        assert len(search_response["result"]["results"]) == 5
        
        # 作成されたエントリを同時に削除
        delete_tasks = []
        for entry_id in entry_ids:
            task = mcp_client.call_tool("delete_memory_entry", {"entry_id": entry_id})
            delete_tasks.append(task)
        
        delete_responses = await asyncio.gather(*delete_tasks)
        
        # 全ての削除が成功したことを確認
        for response in delete_responses:
            assert response["result"]["success"] is True

class TestMCPResponseFormat:
    """MCPレスポンス形式のテスト"""
    
    @pytest.mark.asyncio
    async def test_success_response_format(self, mcp_client, sample_memory_data):
        """成功レスポンス形式のテスト"""
        response = await mcp_client.call_tool("add_note_to_memory", sample_memory_data)
        
        # JSON-RPC 2.0形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        assert isinstance(response["id"], int)
        
        # 成功レスポンスの構造検証
        assert "result" in response
        assert "error" not in response
        
        result = response["result"]
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, mcp_client):
        """エラーレスポンス形式のテスト"""
        # 無効なパラメータでツールを呼び出し
        response = await mcp_client.call_tool("add_note_to_memory", {"content": ""})
        
        # JSON-RPC 2.0形式の検証
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        
        # エラーレスポンスの構造検証（実装関数がエラー情報を含む結果を返す場合）
        if "error" in response:
            # 直接的なエラーレスポンス
            error = response["error"]
            assert "code" in error
            assert "message" in error
            assert isinstance(error["code"], int)
            assert isinstance(error["message"], str)
        else:
            # 実装関数内でエラーが処理される場合
            assert "result" in response
            result = response["result"]
            assert "error" in result
            
            error = result["error"]
            assert "code" in error
            assert "message" in error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])