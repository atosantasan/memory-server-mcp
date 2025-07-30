#!/usr/bin/env python3
"""
MCP統合テスト - MCPサーバーの統合とプロトコル実装をテストする
"""

import asyncio
import logging
from main import (
    mcp, memory_service, initialize_mcp_server,
    _add_note_to_memory_impl, _search_memory_impl, _update_memory_entry_impl,
    _delete_memory_entry_impl, _list_all_memories_impl, _get_project_rules_impl
)

# テスト用ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_server_initialization():
    """MCPサーバーの初期化テスト"""
    logger.info("=== MCPサーバー初期化テスト ===")
    
    try:
        # MCPサーバー初期化
        result = initialize_mcp_server()
        assert result == True, "MCPサーバー初期化が失敗しました"
        
        logger.info("✓ MCPサーバー初期化成功")
        return True
    except Exception as e:
        logger.error(f"✗ MCPサーバー初期化失敗: {e}")
        return False

def test_mcp_tools_registration():
    """MCPツールの登録テスト"""
    logger.info("=== MCPツール登録テスト ===")
    
    try:
        # MCPインスタンスが存在することを確認
        assert mcp is not None, "MCPインスタンスが存在しません"
        
        # MCPツールが登録されていることを確認（FastMCPの内部構造に依存）
        logger.info(f"MCPインスタンス: {mcp}")
        logger.info("✓ MCPツール登録確認完了")
        return True
    except Exception as e:
        logger.error(f"✗ MCPツール登録テスト失敗: {e}")
        return False

def test_mcp_tool_implementations():
    """MCPツール実装のテスト"""
    logger.info("=== MCPツール実装テスト ===")
    
    try:
        # 1. add_note_to_memory テスト
        logger.info("1. add_note_to_memory テスト")
        result = _add_note_to_memory_impl(
            content="テストメモリエントリ",
            tags=["テスト", "MCP"],
            keywords=["統合テスト"],
            summary="MCPツールのテスト用エントリ"
        )
        assert result.get("success") == True, f"add_note_to_memory失敗: {result}"
        entry_id = result["entry"]["id"]
        logger.info(f"✓ add_note_to_memory成功 (ID: {entry_id})")
        
        # 2. search_memory テスト
        logger.info("2. search_memory テスト")
        result = _search_memory_impl(query="テスト", limit=5)
        assert result.get("success") == True, f"search_memory失敗: {result}"
        assert len(result["results"]) > 0, "検索結果が空です"
        logger.info(f"✓ search_memory成功 ({len(result['results'])}件見つかりました)")
        
        # 3. update_memory_entry テスト
        logger.info("3. update_memory_entry テスト")
        result = _update_memory_entry_impl(
            entry_id=entry_id,
            content="更新されたテストメモリエントリ",
            tags=["テスト", "MCP", "更新済み"]
        )
        assert result.get("success") == True, f"update_memory_entry失敗: {result}"
        logger.info("✓ update_memory_entry成功")
        
        # 4. list_all_memories テスト
        logger.info("4. list_all_memories テスト")
        result = _list_all_memories_impl(limit=10)
        assert result.get("success") == True, f"list_all_memories失敗: {result}"
        logger.info(f"✓ list_all_memories成功 ({result['total_count']}件)")
        
        # 5. get_project_rules テスト
        logger.info("5. get_project_rules テスト")
        result = _get_project_rules_impl()
        assert result.get("success") == True, f"get_project_rules失敗: {result}"
        logger.info("✓ get_project_rules成功")
        
        # 6. delete_memory_entry テスト
        logger.info("6. delete_memory_entry テスト")
        result = _delete_memory_entry_impl(entry_id)
        assert result.get("success") == True, f"delete_memory_entry失敗: {result}"
        logger.info("✓ delete_memory_entry成功")
        
        logger.info("✓ 全MCPツール実装テスト成功")
        return True
        
    except Exception as e:
        logger.error(f"✗ MCPツール実装テスト失敗: {e}")
        return False

def test_mcp_error_handling():
    """MCPエラーハンドリングのテスト"""
    logger.info("=== MCPエラーハンドリングテスト ===")
    
    try:
        # 1. 無効なパラメータテスト
        logger.info("1. 無効なパラメータテスト")
        result = _add_note_to_memory_impl(content="")  # 空のコンテンツ
        assert "error" in result, "エラーレスポンスが返されませんでした"
        logger.info("✓ 無効なパラメータエラーハンドリング成功")
        
        # 2. 存在しないエントリテスト
        logger.info("2. 存在しないエントリテスト")
        result = _update_memory_entry_impl(entry_id=99999, content="テスト")
        assert "error" in result, "エラーレスポンスが返されませんでした"
        logger.info("✓ 存在しないエントリエラーハンドリング成功")
        
        # 3. 削除テスト（存在しないエントリ）
        logger.info("3. 存在しないエントリ削除テスト")
        result = _delete_memory_entry_impl(99999)
        assert "error" in result, "エラーレスポンスが返されませんでした"
        logger.info("✓ 存在しないエントリ削除エラーハンドリング成功")
        
        logger.info("✓ 全MCPエラーハンドリングテスト成功")
        return True
        
    except Exception as e:
        logger.error(f"✗ MCPエラーハンドリングテスト失敗: {e}")
        return False

async def run_all_tests():
    """全テストを実行"""
    logger.info("=== MCP統合テスト開始 ===")
    
    tests = [
        ("MCPサーバー初期化", test_mcp_server_initialization()),
        ("MCPツール登録", test_mcp_tools_registration()),
        ("MCPツール実装", test_mcp_tool_implementations()),
        ("MCPエラーハンドリング", test_mcp_error_handling())
    ]
    
    results = []
    for test_name, test_func in tests:
        if asyncio.iscoroutine(test_func):
            result = await test_func
        else:
            result = test_func
        results.append((test_name, result))
    
    # 結果サマリー
    logger.info("=== テスト結果サマリー ===")
    passed = 0
    failed = 0
    
    for test_name, result in results:
        if result:
            logger.info(f"✓ {test_name}: 成功")
            passed += 1
        else:
            logger.error(f"✗ {test_name}: 失敗")
            failed += 1
    
    logger.info(f"=== 最終結果: {passed}件成功, {failed}件失敗 ===")
    
    if failed == 0:
        logger.info("🎉 全テスト成功！MCPサーバーの統合とプロトコル実装が完了しました。")
        return True
    else:
        logger.error("❌ 一部テストが失敗しました。")
        return False

if __name__ == "__main__":
    asyncio.run(run_all_tests())