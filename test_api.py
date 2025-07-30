#!/usr/bin/env python3
"""
REST API統合テスト
FastAPIのTestClientを使用してAPIエンドポイントのテストを実行
"""

import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch

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
def client(setup_test_environment):
    """FastAPIテストクライアントのフィクスチャ"""
    # main.pyをインポート（環境変数設定後）
    from main import app, memory_service
    
    # データベースを初期化
    memory_service.init_database()
    
    # テスト前にデータベースをクリア
    try:
        with memory_service.get_connection() as conn:
            conn.execute("DELETE FROM memory_entries")
            conn.commit()
    except Exception:
        pass  # エラーは無視
    
    # TestClientを作成
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def sample_memory_data():
    """テスト用のサンプルメモリデータ"""
    return {
        "content": "これはテスト用のメモリエントリです",
        "tags": ["テスト", "サンプル"],
        "keywords": ["テスト", "メモリ", "API"],
        "summary": "テスト用のサンプルエントリ"
    }

@pytest.fixture
def created_memory_entry(client, sample_memory_data):
    """事前に作成されたメモリエントリのフィクスチャ"""
    response = client.post("/memories", json=sample_memory_data)
    assert response.status_code == 201
    return response.json()

class TestMemoryEntryCreation:
    """メモリエントリ作成のテスト"""
    
    def test_create_memory_entry_success(self, client, sample_memory_data):
        """正常なメモリエントリ作成のテスト"""
        response = client.post("/memories", json=sample_memory_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # レスポンスの構造を検証
        assert "id" in data
        assert data["content"] == sample_memory_data["content"]
        assert data["tags"] == sample_memory_data["tags"]
        assert data["keywords"] == sample_memory_data["keywords"]
        assert data["summary"] == sample_memory_data["summary"]
        assert "created_at" in data
        assert "updated_at" in data
        
        # IDが正の整数であることを確認
        assert isinstance(data["id"], int)
        assert data["id"] > 0
    
    def test_create_memory_entry_minimal_data(self, client):
        """最小限のデータでのメモリエントリ作成テスト"""
        minimal_data = {"content": "最小限のメモリエントリ"}
        response = client.post("/memories", json=minimal_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["content"] == minimal_data["content"]
        assert data["tags"] == []
        assert data["keywords"] == []
        assert data["summary"] == ""
    
    def test_create_memory_entry_empty_content(self, client):
        """空のコンテンツでのメモリエントリ作成エラーテスト"""
        invalid_data = {"content": ""}
        response = client.post("/memories", json=invalid_data)
        
        assert response.status_code == 422  # Pydanticバリデーションエラー
    
    def test_create_memory_entry_missing_content(self, client):
        """コンテンツなしでのメモリエントリ作成エラーテスト"""
        invalid_data = {"tags": ["テスト"]}
        response = client.post("/memories", json=invalid_data)
        
        assert response.status_code == 422  # Pydanticバリデーションエラー
    
    def test_create_memory_entry_invalid_tags(self, client):
        """無効なタグでのメモリエントリ作成テスト"""
        invalid_data = {
            "content": "テストコンテンツ",
            "tags": "文字列（リストではない）"
        }
        response = client.post("/memories", json=invalid_data)
        
        assert response.status_code == 422  # Pydanticバリデーションエラー

class TestMemoryEntryRetrieval:
    """メモリエントリ取得のテスト"""
    
    def test_get_memory_entry_success(self, client, created_memory_entry):
        """正常なメモリエントリ取得のテスト"""
        entry_id = created_memory_entry["id"]
        response = client.get(f"/memories/{entry_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # 作成されたエントリと同じデータが返されることを確認
        assert data["id"] == created_memory_entry["id"]
        assert data["content"] == created_memory_entry["content"]
        assert data["tags"] == created_memory_entry["tags"]
        assert data["keywords"] == created_memory_entry["keywords"]
        assert data["summary"] == created_memory_entry["summary"]
    
    def test_get_memory_entry_not_found(self, client):
        """存在しないメモリエントリの取得エラーテスト"""
        response = client.get("/memories/99999")
        
        assert response.status_code == 404
        data = response.json()
        
        # エラーレスポンスの構造を検証
        assert "error" in data
        assert data["error"]["code"] == "MEMORY_NOT_FOUND"
    
    def test_get_memory_entry_invalid_id(self, client):
        """無効なIDでのメモリエントリ取得エラーテスト"""
        response = client.get("/memories/0")
        
        assert response.status_code == 400
        data = response.json()
        
        # 新しいエラーレスポンス形式に対応
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

class TestMemoryEntryUpdate:
    """メモリエントリ更新のテスト"""
    
    def test_update_memory_entry_success(self, client, created_memory_entry):
        """正常なメモリエントリ更新のテスト"""
        entry_id = created_memory_entry["id"]
        update_data = {
            "content": "更新されたコンテンツ",
            "tags": ["更新", "テスト"],
            "summary": "更新されたサマリー"
        }
        
        response = client.put(f"/memories/{entry_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # 更新されたデータが反映されていることを確認
        assert data["id"] == entry_id
        assert data["content"] == update_data["content"]
        assert data["tags"] == update_data["tags"]
        assert data["summary"] == update_data["summary"]
        # keywordsは更新されていないので元の値のまま
        assert data["keywords"] == created_memory_entry["keywords"]
    
    def test_update_memory_entry_partial(self, client, created_memory_entry):
        """部分的なメモリエントリ更新のテスト"""
        entry_id = created_memory_entry["id"]
        update_data = {"content": "部分更新されたコンテンツ"}
        
        response = client.put(f"/memories/{entry_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # 指定されたフィールドのみ更新されていることを確認
        assert data["content"] == update_data["content"]
        assert data["tags"] == created_memory_entry["tags"]  # 変更されていない
        assert data["keywords"] == created_memory_entry["keywords"]  # 変更されていない
        assert data["summary"] == created_memory_entry["summary"]  # 変更されていない
    
    def test_update_memory_entry_not_found(self, client):
        """存在しないメモリエントリの更新エラーテスト"""
        update_data = {"content": "存在しないエントリの更新"}
        response = client.put("/memories/99999", json=update_data)
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data
        assert data["error"]["code"] == "MEMORY_NOT_FOUND"
    
    def test_update_memory_entry_empty_content(self, client, created_memory_entry):
        """空のコンテンツでの更新エラーテスト"""
        entry_id = created_memory_entry["id"]
        update_data = {"content": ""}
        
        response = client.put(f"/memories/{entry_id}", json=update_data)
        
        assert response.status_code == 422  # Pydanticバリデーションエラー

class TestMemoryEntryDeletion:
    """メモリエントリ削除のテスト"""
    
    def test_delete_memory_entry_success(self, client, created_memory_entry):
        """正常なメモリエントリ削除のテスト"""
        entry_id = created_memory_entry["id"]
        response = client.delete(f"/memories/{entry_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # 削除成功レスポンスの構造を検証
        assert data["success"] is True
        assert "message" in data
        assert data["data"]["deleted_entry_id"] == entry_id
        
        # 削除されたエントリが取得できないことを確認
        get_response = client.get(f"/memories/{entry_id}")
        assert get_response.status_code == 404
    
    def test_delete_memory_entry_not_found(self, client):
        """存在しないメモリエントリの削除エラーテスト"""
        response = client.delete("/memories/99999")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data
        assert data["error"]["code"] == "MEMORY_NOT_FOUND"
    
    def test_delete_memory_entry_invalid_id(self, client):
        """無効なIDでのメモリエントリ削除エラーテスト"""
        response = client.delete("/memories/0")
        
        assert response.status_code == 400
        data = response.json()
        
        # 新しいエラーレスポンス形式に対応
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

class TestMemoryEntryListing:
    """メモリエントリ一覧表示のテスト"""
    
    def test_list_memories_empty(self, client):
        """空のメモリリスト取得のテスト"""
        response = client.get("/memories")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "total_count" in data
        assert data["entries"] == []
        assert data["total_count"] == 0
    
    def test_list_memories_with_data(self, client, sample_memory_data):
        """データありのメモリリスト取得のテスト"""
        # 複数のエントリを作成
        entries = []
        for i in range(3):
            entry_data = sample_memory_data.copy()
            entry_data["content"] = f"テストエントリ {i+1}"
            entry_data["tags"] = [f"タグ{i+1}"]
            
            response = client.post("/memories", json=entry_data)
            assert response.status_code == 201
            entries.append(response.json())
        
        # リスト取得
        response = client.get("/memories")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) == 3
        assert data["total_count"] == 3
        
        # 最新のエントリが最初に来ることを確認（updated_at DESC順）
        assert data["entries"][0]["content"] == "テストエントリ 3"
    
    def test_list_memories_with_limit(self, client, sample_memory_data):
        """制限付きメモリリスト取得のテスト"""
        # 5つのエントリを作成
        for i in range(5):
            entry_data = sample_memory_data.copy()
            entry_data["content"] = f"制限テストエントリ {i+1}"
            
            response = client.post("/memories", json=entry_data)
            assert response.status_code == 201
        
        # 制限付きでリスト取得
        response = client.get("/memories?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) == 3
        assert data["total_count"] == 3
        assert data["limit"] == 3

class TestMemoryEntrySearch:
    """メモリエントリ検索のテスト"""
    
    def test_search_memories_by_query(self, client, sample_memory_data):
        """クエリによるメモリ検索のテスト"""
        # 検索用のエントリを作成
        search_data = sample_memory_data.copy()
        search_data["content"] = "特別な検索対象コンテンツ"
        search_data["summary"] = "検索テスト用サマリー"
        
        response = client.post("/memories", json=search_data)
        assert response.status_code == 201
        
        # 別のエントリも作成（検索にヒットしないもの）
        other_data = sample_memory_data.copy()
        other_data["content"] = "通常のコンテンツ"
        other_data["summary"] = "通常のサマリー"
        
        response = client.post("/memories", json=other_data)
        assert response.status_code == 201
        
        # 検索実行
        response = client.get("/memories/search?q=特別な検索対象")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) == 1
        assert data["entries"][0]["content"] == "特別な検索対象コンテンツ"
    
    def test_search_memories_by_tags(self, client, sample_memory_data):
        """タグによるメモリ検索のテスト"""
        # タグ付きエントリを作成
        tagged_data = sample_memory_data.copy()
        tagged_data["content"] = "タグ検索テスト"
        tagged_data["tags"] = ["特別タグ", "検索用"]
        
        response = client.post("/memories", json=tagged_data)
        assert response.status_code == 201
        
        # 別のタグのエントリも作成
        other_tagged_data = sample_memory_data.copy()
        other_tagged_data["content"] = "別のタグテスト"
        other_tagged_data["tags"] = ["通常タグ"]
        
        response = client.post("/memories", json=other_tagged_data)
        assert response.status_code == 201
        
        # タグ検索実行
        response = client.get("/memories/search?tags=特別タグ")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) == 1
        assert data["entries"][0]["content"] == "タグ検索テスト"
    
    def test_search_memories_combined(self, client, sample_memory_data):
        """クエリとタグの組み合わせ検索のテスト"""
        # 組み合わせ検索用エントリを作成
        combined_data = sample_memory_data.copy()
        combined_data["content"] = "組み合わせ検索テストコンテンツ"
        combined_data["tags"] = ["組み合わせ", "テスト"]
        
        response = client.post("/memories", json=combined_data)
        assert response.status_code == 201
        
        # 組み合わせ検索実行
        response = client.get("/memories/search?q=組み合わせ&tags=テスト")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) == 1
        assert data["entries"][0]["content"] == "組み合わせ検索テストコンテンツ"
    
    def test_search_memories_no_results(self, client):
        """検索結果なしのテスト"""
        response = client.get("/memories/search?q=存在しない検索語")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["entries"] == []
        assert data["total_count"] == 0

class TestMemoryEntryTagFiltering:
    """タグによるフィルタリングのテスト"""
    
    def test_get_memories_by_tag_success(self, client, sample_memory_data):
        """正常なタグフィルタリングのテスト"""
        # 特定のタグ付きエントリを作成
        tagged_data = sample_memory_data.copy()
        tagged_data["content"] = "タグフィルタリングテスト"
        tagged_data["tags"] = ["フィルタータグ", "テスト"]
        
        response = client.post("/memories", json=tagged_data)
        assert response.status_code == 201
        
        # タグフィルタリング実行
        response = client.get("/memories/tags/フィルタータグ")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) == 1
        assert data["entries"][0]["content"] == "タグフィルタリングテスト"
    
    def test_get_memories_by_tag_empty(self, client):
        """存在しないタグでのフィルタリングテスト"""
        response = client.get("/memories/tags/存在しないタグ")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["entries"] == []
        assert data["total_count"] == 0
    
    def test_get_memories_by_tag_empty_tag(self, client):
        """空のタグでのフィルタリングエラーテスト"""
        response = client.get("/memories/tags/")
        
        # FastAPIのルーティングにより422が返される（パスパラメータが空）
        assert response.status_code == 422

class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_invalid_json_request(self, client):
        """無効なJSONリクエストのテスト"""
        response = client.post(
            "/memories",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_unsupported_http_method(self, client):
        """サポートされていないHTTPメソッドのテスト"""
        response = client.patch("/memories/1")
        
        assert response.status_code == 405  # Method Not Allowed
    
    def test_invalid_endpoint(self, client):
        """存在しないエンドポイントのテスト"""
        response = client.get("/invalid-endpoint")
        
        assert response.status_code == 404

class TestResponseFormat:
    """レスポンス形式のテスト"""
    
    def test_memory_entry_response_format(self, client, created_memory_entry):
        """メモリエントリレスポンス形式のテスト"""
        entry_id = created_memory_entry["id"]
        response = client.get(f"/memories/{entry_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # 必須フィールドの存在確認
        required_fields = ["id", "content", "tags", "keywords", "summary", "created_at", "updated_at"]
        for field in required_fields:
            assert field in data
        
        # データ型の確認
        assert isinstance(data["id"], int)
        assert isinstance(data["content"], str)
        assert isinstance(data["tags"], list)
        assert isinstance(data["keywords"], list)
        assert isinstance(data["summary"], str)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
    
    def test_memory_list_response_format(self, client, created_memory_entry):
        """メモリリストレスポンス形式のテスト"""
        response = client.get("/memories")
        
        assert response.status_code == 200
        data = response.json()
        
        # リストレスポンスの構造確認
        assert "entries" in data
        assert "total_count" in data
        assert isinstance(data["entries"], list)
        assert isinstance(data["total_count"], int)
        
        # エントリが存在する場合の形式確認
        if data["entries"]:
            entry = data["entries"][0]
            required_fields = ["id", "content", "tags", "keywords", "summary", "created_at", "updated_at"]
            for field in required_fields:
                assert field in entry
    
    def test_error_response_format(self, client):
        """エラーレスポンス形式のテスト"""
        response = client.get("/memories/99999")
        
        assert response.status_code == 404
        data = response.json()
        
        # エラーレスポンスの構造確認
        assert "error" in data
        
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error
        
        assert isinstance(error["code"], str)
        assert isinstance(error["message"], str)
        assert isinstance(error["details"], dict)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])