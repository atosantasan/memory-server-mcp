#!/usr/bin/env python3
"""
Unit tests for MCP tools
Tests all MCP tool functions including error cases and edge cases
"""

import pytest
import tempfile
import os
import sqlite3
from typing import List, Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Import the MCP tool implementation functions and related classes
from main import (
    _add_note_to_memory_impl,
    _search_memory_impl,
    _update_memory_entry_impl,
    _delete_memory_entry_impl,
    _list_all_memories_impl,
    _get_project_rules_impl,
    MemoryService,
    NotFoundError,
    ValidationError,
    DatabaseError,
    MCPError,
    ErrorCodes,
    Config
)


class TestMCPTools:
    """Base test class for MCP tools"""
    
    @pytest.fixture
    def memory_service_mock(self):
        """Create a mock MemoryService for testing"""
        return MagicMock(spec=MemoryService)
    
    @pytest.fixture
    def sample_memory_entry(self):
        """Sample memory entry data for testing"""
        return {
            "id": 1,
            "content": "Test memory content",
            "tags": ["test", "sample"],
            "keywords": ["memory", "testing"],
            "summary": "A test memory entry",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        }
    
    @pytest.fixture
    def multiple_memory_entries(self):
        """Multiple memory entries for testing"""
        return [
            {
                "id": 1,
                "content": "Python programming rules",
                "tags": ["programming", "python", "rules"],
                "keywords": ["python", "coding"],
                "summary": "Python best practices",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            },
            {
                "id": 2,
                "content": "Database design principles",
                "tags": ["database", "design", "rules"],
                "keywords": ["database", "sql"],
                "summary": "DB design guidelines",
                "created_at": "2025-01-01T01:00:00",
                "updated_at": "2025-01-01T01:00:00"
            },
            {
                "id": 3,
                "content": "API development guidelines",
                "tags": ["api", "development"],
                "keywords": ["api", "rest"],
                "summary": "API best practices",
                "created_at": "2025-01-01T02:00:00",
                "updated_at": "2025-01-01T02:00:00"
            }
        ]


class TestAddNoteToMemory(TestMCPTools):
    """Test add_note_to_memory MCP tool"""
    
    @patch('main.memory_service')
    def test_add_note_success(self, mock_service, sample_memory_entry):
        """Test successful note addition"""
        mock_service.add_memory.return_value = 1
        mock_service.get_memory_by_id.return_value = sample_memory_entry
        
        result = _add_note_to_memory_impl(
            content="Test content",
            tags=["test"],
            keywords=["testing"],
            summary="Test summary"
        )
        
        assert result["success"] is True
        assert "メモリエントリが正常に追加されました" in result["message"]
        assert "entry" in result
        assert result["entry"] == sample_memory_entry
        
        # Verify service was called correctly
        mock_service.add_memory.assert_called_once_with(
            content="Test content",
            tags=["test"],
            keywords=["testing"],
            summary="Test summary"
        )
    
    @patch('main.memory_service')
    def test_add_note_minimal_data(self, mock_service, sample_memory_entry):
        """Test adding note with minimal data"""
        mock_service.add_memory.return_value = 1
        mock_service.get_memory_by_id.return_value = sample_memory_entry
        
        result = _add_note_to_memory_impl(content="Minimal content")
        
        assert result["success"] is True
        assert "entry" in result
        
        # Verify service was called with defaults (empty lists, not None)
        mock_service.add_memory.assert_called_once_with(
            content="Minimal content",
            tags=[],
            keywords=[],
            summary=None
        )
    
    @patch('main.memory_service')
    def test_add_note_validation_error(self, mock_service):
        """Test handling of validation errors"""
        mock_service.add_memory.side_effect = ValidationError("Content cannot be empty", "content", "")
        
        result = _add_note_to_memory_impl(content="")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Content cannot be empty" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_add_note_database_error(self, mock_service):
        """Test handling of database errors"""
        mock_service.add_memory.side_effect = DatabaseError("Database connection failed", "insert")
        
        result = _add_note_to_memory_impl(content="Test content")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        assert "データベース操作中にエラーが発生しました" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_add_note_unexpected_error(self, mock_service):
        """Test handling of unexpected errors"""
        mock_service.add_memory.side_effect = Exception("Unexpected error")
        
        result = _add_note_to_memory_impl(content="Test content")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        assert "予期しないエラーが発生しました" in result["error"]["message"]


class TestSearchMemory(TestMCPTools):
    """Test search_memory MCP tool"""
    
    @patch('main.memory_service')
    def test_search_memory_by_query(self, mock_service, multiple_memory_entries):
        """Test searching memory by query"""
        mock_service.search_memories.return_value = multiple_memory_entries[:2]
        
        result = _search_memory_impl(query="python", limit=10)
        
        assert result["success"] is True
        assert len(result["results"]) == 2
        assert "2件のメモリエントリが見つかりました" in result["message"]
        assert result["search_params"]["query"] == "python"
        
        mock_service.search_memories.assert_called_once_with(
            query="python",
            tags=None,
            limit=10
        )
    
    @patch('main.memory_service')
    def test_search_memory_by_tags(self, mock_service, multiple_memory_entries):
        """Test searching memory by tags"""
        mock_service.search_memories.return_value = [multiple_memory_entries[0]]
        
        result = _search_memory_impl(tags=["rules"], limit=10)
        
        assert result["success"] is True
        assert len(result["results"]) == 1
        assert "1件のメモリエントリが見つかりました" in result["message"]
        assert result["search_params"]["tags"] == ["rules"]
        
        mock_service.search_memories.assert_called_once_with(
            query=None,
            tags=["rules"],
            limit=10
        )
    
    @patch('main.memory_service')
    def test_search_memory_by_query_and_tags(self, mock_service, multiple_memory_entries):
        """Test searching memory by both query and tags"""
        mock_service.search_memories.return_value = [multiple_memory_entries[0]]
        
        result = _search_memory_impl(query="python", tags=["rules"], limit=5)
        
        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["search_params"]["query"] == "python"
        assert result["search_params"]["tags"] == ["rules"]
        
        mock_service.search_memories.assert_called_once_with(
            query="python",
            tags=["rules"],
            limit=5
        )
    
    @patch('main.memory_service')
    def test_search_memory_no_results(self, mock_service):
        """Test search with no results"""
        mock_service.search_memories.return_value = []
        
        result = _search_memory_impl(query="nonexistent")
        
        assert result["success"] is True
        assert len(result["results"]) == 0
        assert "0件のメモリエントリが見つかりました" in result["message"]
    
    @patch('main.memory_service')
    def test_search_memory_database_error(self, mock_service):
        """Test handling of database errors in search"""
        mock_service.search_memories.side_effect = DatabaseError("Search failed", "search")
        
        result = _search_memory_impl(query="test")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        assert "データベース操作中にエラーが発生しました" in result["error"]["message"]


class TestUpdateMemoryEntry(TestMCPTools):
    """Test update_memory_entry MCP tool"""
    
    @patch('main.memory_service')
    def test_update_memory_success(self, mock_service, sample_memory_entry):
        """Test successful memory update"""
        updated_entry = sample_memory_entry.copy()
        updated_entry["content"] = "Updated content"
        
        mock_service.update_memory.return_value = True
        mock_service.get_memory_by_id.return_value = updated_entry
        
        result = _update_memory_entry_impl(
            entry_id=1,
            content="Updated content",
            tags=["updated"],
            keywords=["new"],
            summary="Updated summary"
        )
        
        assert result["success"] is True
        assert "メモリエントリが正常に更新されました (ID: 1)" in result["message"]
        assert "entry" in result
        
        mock_service.update_memory.assert_called_once_with(
            entry_id=1,
            content="Updated content",
            tags=["updated"],
            keywords=["new"],
            summary="Updated summary"
        )
    
    @patch('main.memory_service')
    def test_update_memory_partial_update(self, mock_service, sample_memory_entry):
        """Test partial memory update"""
        mock_service.update_memory.return_value = True
        mock_service.get_memory_by_id.return_value = sample_memory_entry
        
        result = _update_memory_entry_impl(entry_id=1, content="New content only")
        
        assert result["success"] is True
        
        mock_service.update_memory.assert_called_once_with(
            entry_id=1,
            content="New content only",
            tags=None,
            keywords=None,
            summary=None
        )
    
    @patch('main.memory_service')
    def test_update_memory_not_found(self, mock_service):
        """Test updating non-existent memory entry"""
        mock_service.update_memory.side_effect = NotFoundError("Memory entry not found", 999)
        
        result = _update_memory_entry_impl(entry_id=999, content="New content")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Memory entry not found" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_update_memory_validation_error(self, mock_service):
        """Test update with validation error"""
        mock_service.update_memory.side_effect = ValidationError("Content cannot be empty", "content", "")
        
        result = _update_memory_entry_impl(entry_id=1, content="")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Content cannot be empty" in result["error"]["message"]


class TestDeleteMemoryEntry(TestMCPTools):
    """Test delete_memory_entry MCP tool"""
    
    @patch('main.memory_service')
    def test_delete_memory_success(self, mock_service):
        """Test successful memory deletion"""
        mock_service.delete_memory.return_value = True
        
        result = _delete_memory_entry_impl(entry_id=1)
        
        assert result["success"] is True
        assert result["deleted_entry_id"] == 1
        assert "メモリエントリが正常に削除されました (ID: 1)" in result["message"]
        
        mock_service.delete_memory.assert_called_once_with(1)
    
    @patch('main.memory_service')
    def test_delete_memory_not_found(self, mock_service):
        """Test deleting non-existent memory entry"""
        mock_service.delete_memory.side_effect = NotFoundError("Memory entry not found", 999)
        
        result = _delete_memory_entry_impl(entry_id=999)
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Memory entry not found" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_delete_memory_database_error(self, mock_service):
        """Test handling of database errors in deletion"""
        mock_service.delete_memory.side_effect = DatabaseError("Delete failed", "delete")
        
        result = _delete_memory_entry_impl(entry_id=1)
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        assert "データベース操作中にエラーが発生しました" in result["error"]["message"]


class TestListAllMemories(TestMCPTools):
    """Test list_all_memories MCP tool"""
    
    @patch('main.memory_service')
    def test_list_all_memories_success(self, mock_service, multiple_memory_entries):
        """Test successful listing of all memories"""
        # Add metadata to entries as the service would
        entries_with_metadata = []
        for entry in multiple_memory_entries:
            entry_with_meta = entry.copy()
            entry_with_meta["metadata"] = {
                "tag_count": len(entry["tags"]),
                "keyword_count": len(entry["keywords"]),
                "content_length": len(entry["content"]),
                "has_summary": bool(entry["summary"])
            }
            entries_with_metadata.append(entry_with_meta)
        
        mock_service.list_all_memories.return_value = entries_with_metadata
        
        result = _list_all_memories_impl(limit=50)
        
        assert result["success"] is True
        assert len(result["entries"]) == 3
        assert result["total_count"] == 3
        assert result["limit"] == 50
        assert "3件のメモリエントリを取得しました" in result["message"]
        
        # Verify metadata is included
        for entry in result["entries"]:
            assert "metadata" in entry
            assert "tag_count" in entry["metadata"]
        
        mock_service.list_all_memories.assert_called_once_with(limit=50)
    
    @patch('main.memory_service')
    def test_list_all_memories_empty(self, mock_service):
        """Test listing memories from empty database"""
        mock_service.list_all_memories.return_value = []
        
        result = _list_all_memories_impl()
        
        assert result["success"] is True
        assert len(result["entries"]) == 0
        assert result["total_count"] == 0
        assert "0件のメモリエントリを取得しました" in result["message"]
    
    @patch('main.memory_service')
    def test_list_all_memories_with_limit(self, mock_service, multiple_memory_entries):
        """Test listing memories with custom limit"""
        mock_service.list_all_memories.return_value = multiple_memory_entries[:2]
        
        result = _list_all_memories_impl(limit=2)
        
        assert result["success"] is True
        assert len(result["entries"]) == 2
        assert result["limit"] == 2
        
        mock_service.list_all_memories.assert_called_once_with(limit=2)
    
    @patch('main.memory_service')
    def test_list_all_memories_database_error(self, mock_service):
        """Test handling of database errors in listing"""
        mock_service.list_all_memories.side_effect = DatabaseError("List failed", "list")
        
        result = _list_all_memories_impl()
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        assert "データベース操作中にエラーが発生しました" in result["error"]["message"]


class TestGetProjectRules(TestMCPTools):
    """Test get_project_rules MCP tool"""
    
    @patch('main.memory_service')
    def test_get_project_rules_success(self, mock_service, multiple_memory_entries):
        """Test successful retrieval of project rules"""
        # Filter entries with "rules" tag
        rules_entries = [entry for entry in multiple_memory_entries if "rules" in entry["tags"]]
        mock_service.search_memories.return_value = rules_entries
        
        result = _get_project_rules_impl()
        
        assert result["success"] is True
        assert len(result["rules"]) == 2  # Two entries have "rules" tag
        assert "2件のプロジェクトルールが見つかりました" in result["message"]
        
        # Verify all returned entries have "rules" tag
        for rule in result["rules"]:
            assert "rules" in rule["tags"]
        
        # Verify the correct rule tags are searched
        expected_tags = ["ルール", "rule", "rules", "規則", "原則", "方針"]
        mock_service.search_memories.assert_called_once_with(
            query=None,
            tags=expected_tags,
            limit=Config.MAX_SEARCH_RESULTS
        )
    
    @patch('main.memory_service')
    def test_get_project_rules_no_rules(self, mock_service):
        """Test retrieval when no project rules exist"""
        mock_service.search_memories.return_value = []
        
        result = _get_project_rules_impl()
        
        assert result["success"] is True
        assert len(result["rules"]) == 0
        assert "0件のプロジェクトルールが見つかりました" in result["message"]
    
    @patch('main.memory_service')
    def test_get_project_rules_database_error(self, mock_service):
        """Test handling of database errors in rules retrieval"""
        mock_service.search_memories.side_effect = DatabaseError("Search failed", "search")
        
        result = _get_project_rules_impl()
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        assert "データベース操作中にエラーが発生しました" in result["error"]["message"]


class TestMCPToolsEdgeCases(TestMCPTools):
    """Test edge cases and error scenarios for MCP tools"""
    
    @patch('main.memory_service')
    def test_add_note_with_empty_content(self, mock_service):
        """Test adding note with empty content"""
        result = _add_note_to_memory_impl(content="")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Content cannot be empty" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_add_note_with_whitespace_only_content(self, mock_service):
        """Test adding note with whitespace-only content"""
        result = _add_note_to_memory_impl(content="   ")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Content cannot be empty" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_add_note_with_empty_lists(self, mock_service, sample_memory_entry):
        """Test adding note with empty tags and keywords lists"""
        mock_service.add_memory.return_value = 1
        mock_service.get_memory_by_id.return_value = sample_memory_entry
        
        result = _add_note_to_memory_impl(
            content="Test content",
            tags=[],
            keywords=[],
            summary=""
        )
        
        assert result["success"] is True
        mock_service.add_memory.assert_called_once_with(
            content="Test content",
            tags=[],
            keywords=[],
            summary=None  # The implementation converts empty string to None
        )
    
    @patch('main.memory_service')
    def test_search_memory_with_zero_limit(self, mock_service):
        """Test search with zero limit"""
        mock_service.search_memories.return_value = []
        
        result = _search_memory_impl(query="test", limit=0)
        
        # Should use default limit when 0 is provided
        mock_service.search_memories.assert_called_once_with(
            query="test",
            tags=None,
            limit=10  # Should be corrected to default
        )
    
    @patch('main.memory_service')
    def test_search_memory_with_excessive_limit(self, mock_service):
        """Test search with limit exceeding maximum"""
        mock_service.search_memories.return_value = []
        
        result = _search_memory_impl(query="test", limit=1000)
        
        # Should use default limit when excessive limit is provided
        mock_service.search_memories.assert_called_once_with(
            query="test",
            tags=None,
            limit=10  # Should be corrected to default
        )
    
    @patch('main.memory_service')
    def test_search_memory_with_empty_query_and_tags(self, mock_service):
        """Test search with empty query and tags"""
        mock_service.search_memories.return_value = []
        
        result = _search_memory_impl(query="", tags=[])
        
        assert result["success"] is True
        mock_service.search_memories.assert_called_once_with(
            query=None,
            tags=None,
            limit=10
        )
    
    @patch('main.memory_service')
    def test_update_memory_with_invalid_entry_id(self, mock_service):
        """Test updating memory with invalid entry ID"""
        result = _update_memory_entry_impl(entry_id=0, content="New content")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Entry ID must be a positive integer" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_update_memory_with_negative_entry_id(self, mock_service):
        """Test updating memory with negative entry ID"""
        result = _update_memory_entry_impl(entry_id=-1, content="New content")
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Entry ID must be a positive integer" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_update_memory_with_none_values(self, mock_service, sample_memory_entry):
        """Test updating memory with None values (should not update those fields)"""
        mock_service.update_memory.return_value = True
        mock_service.get_memory_by_id.return_value = sample_memory_entry
        
        result = _update_memory_entry_impl(
            entry_id=1,
            content=None,
            tags=None,
            keywords=None,
            summary=None
        )
        
        assert result["success"] is True
        mock_service.update_memory.assert_called_once_with(
            entry_id=1,
            content=None,
            tags=None,
            keywords=None,
            summary=None
        )
    
    @patch('main.memory_service')
    def test_delete_memory_with_invalid_entry_id(self, mock_service):
        """Test deleting memory with invalid entry ID"""
        result = _delete_memory_entry_impl(entry_id=0)
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Entry ID must be a positive integer" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_delete_memory_with_negative_entry_id(self, mock_service):
        """Test deleting memory with negative entry ID"""
        result = _delete_memory_entry_impl(entry_id=-1)
        
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        assert "Entry ID must be a positive integer" in result["error"]["message"]
    
    @patch('main.memory_service')
    def test_list_memories_with_negative_limit(self, mock_service):
        """Test listing memories with negative limit"""
        mock_service.list_all_memories.return_value = []
        
        result = _list_all_memories_impl(limit=-1)
        
        # The implementation corrects negative limits to default (50)
        mock_service.list_all_memories.assert_called_once_with(limit=50)
    
    @patch('main.memory_service')
    def test_list_memories_with_zero_limit(self, mock_service):
        """Test listing memories with zero limit"""
        mock_service.list_all_memories.return_value = []
        
        result = _list_all_memories_impl(limit=0)
        
        # The implementation corrects zero limits to default (50)
        mock_service.list_all_memories.assert_called_once_with(limit=50)
    
    def test_mcp_error_response_format(self):
        """Test MCP error response format"""
        from main import ErrorResponse
        
        error_response = ErrorResponse.create_mcp_error_response(
            code=-32602,
            message="Invalid params",
            data={"field": "test"}
        )
        
        assert "error" in error_response
        assert error_response["error"]["code"] == -32602
        assert error_response["error"]["message"] == "Invalid params"
        assert error_response["error"]["data"]["field"] == "test"


class TestMCPToolsIntegration(TestMCPTools):
    """Integration tests for MCP tools with real database"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def real_memory_service(self, temp_db_path):
        """Create a real MemoryService instance for integration testing"""
        return MemoryService(temp_db_path)
    
    @patch('main.memory_service')
    def test_add_and_retrieve_memory_integration(self, mock_service, real_memory_service):
        """Integration test: add memory and retrieve it"""
        # Replace the mock with real service for this test
        mock_service.side_effect = lambda *args, **kwargs: getattr(real_memory_service, mock_service._mock_name)(*args, **kwargs)
        mock_service.add_memory = real_memory_service.add_memory
        mock_service.get_memory_by_id = real_memory_service.get_memory_by_id
        
        # Add a memory entry
        result = _add_note_to_memory_impl(
            content="Integration test content",
            tags=["integration", "test"],
            keywords=["testing", "memory"],
            summary="Integration test summary"
        )
        
        assert result["success"] is True
        entry_id = result["entry"]["id"]
        
        # Verify the entry was created correctly
        assert result["entry"]["content"] == "Integration test content"
        assert result["entry"]["tags"] == ["integration", "test"]
        assert result["entry"]["keywords"] == ["testing", "memory"]
        assert result["entry"]["summary"] == "Integration test summary"
    
    @patch('main.memory_service')
    def test_search_memory_integration(self, mock_service, real_memory_service):
        """Integration test: add multiple memories and search them"""
        mock_service.add_memory = real_memory_service.add_memory
        mock_service.search_memories = real_memory_service.search_memories
        
        # Add multiple memory entries
        entries_data = [
            ("Python programming guide", ["programming", "python"], ["python", "guide"]),
            ("Database design principles", ["database", "design"], ["database", "sql"]),
            ("Python testing best practices", ["programming", "python", "testing"], ["python", "test"])
        ]
        
        for content, tags, keywords in entries_data:
            real_memory_service.add_memory(content=content, tags=tags, keywords=keywords)
        
        # Search by query
        result = _search_memory_impl(query="python")
        assert result["success"] is True
        assert len(result["results"]) >= 2  # Should find Python-related entries
        
        # Search by tags
        result = _search_memory_impl(tags=["programming"])
        assert result["success"] is True
        assert len(result["results"]) >= 2  # Should find programming-related entries
    
    @patch('main.memory_service')
    def test_update_and_delete_memory_integration(self, mock_service, real_memory_service):
        """Integration test: add, update, and delete memory"""
        mock_service.add_memory = real_memory_service.add_memory
        mock_service.get_memory_by_id = real_memory_service.get_memory_by_id
        mock_service.update_memory = real_memory_service.update_memory
        mock_service.delete_memory = real_memory_service.delete_memory
        
        # Add a memory entry
        entry_id = real_memory_service.add_memory(
            content="Original content",
            tags=["original"],
            keywords=["test"]
        )
        
        # Update the entry
        result = _update_memory_entry_impl(
            entry_id=entry_id,
            content="Updated content",
            tags=["updated"],
            keywords=["modified"]
        )
        
        assert result["success"] is True
        assert result["entry"]["content"] == "Updated content"
        assert result["entry"]["tags"] == ["updated"]
        assert result["entry"]["keywords"] == ["modified"]
        
        # Delete the entry
        result = _delete_memory_entry_impl(entry_id=entry_id)
        assert result["success"] is True
        assert result["deleted_entry_id"] == entry_id
        
        # Verify entry is deleted
        try:
            real_memory_service.get_memory_by_id(entry_id)
            assert False, "Entry should have been deleted"
        except NotFoundError:
            pass  # Expected behavior


class TestMCPToolsParameterValidation(TestMCPTools):
    """Test parameter validation for MCP tools"""
    
    def test_add_note_parameter_validation(self):
        """Test parameter validation for add_note_to_memory"""
        # Test with None content
        result = _add_note_to_memory_impl(content=None)
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
    
    def test_update_memory_parameter_validation(self):
        """Test parameter validation for update_memory_entry"""
        # Test with string entry_id
        result = _update_memory_entry_impl(entry_id="invalid", content="test")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        
        # Test with float entry_id
        result = _update_memory_entry_impl(entry_id=1.5, content="test")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
    
    def test_delete_memory_parameter_validation(self):
        """Test parameter validation for delete_memory_entry"""
        # Test with string entry_id
        result = _delete_memory_entry_impl(entry_id="invalid")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        
        # Test with float entry_id
        result = _delete_memory_entry_impl(entry_id=1.5)
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
    
    @patch('main.memory_service')
    def test_search_memory_limit_validation(self, mock_service):
        """Test limit validation for search_memory"""
        mock_service.search_memories.return_value = []
        
        # Test with negative limit - should be corrected to default
        result = _search_memory_impl(query="test", limit=-5)
        assert result["success"] is True
        mock_service.search_memories.assert_called_once_with(
            query="test",
            tags=None,
            limit=10  # Should be corrected to default
        )
    
    @patch('main.memory_service')
    def test_list_memories_limit_validation(self, mock_service):
        """Test limit validation for list_all_memories"""
        mock_service.list_all_memories.return_value = []
        
        # Test with excessive limit - should be corrected
        result = _list_all_memories_impl(limit=1000)
        assert result["success"] is True
        mock_service.list_all_memories.assert_called_once_with(limit=50)


class TestMCPToolsErrorHandling(TestMCPTools):
    """Test comprehensive error handling for MCP tools"""
    
    @patch('main.memory_service')
    def test_all_tools_handle_database_errors(self, mock_service):
        """Test that all MCP tools properly handle database errors"""
        mock_service.add_memory.side_effect = DatabaseError("DB connection failed", "insert")
        mock_service.search_memories.side_effect = DatabaseError("DB connection failed", "search")
        mock_service.update_memory.side_effect = DatabaseError("DB connection failed", "update")
        mock_service.delete_memory.side_effect = DatabaseError("DB connection failed", "delete")
        mock_service.list_all_memories.side_effect = DatabaseError("DB connection failed", "list")
        
        # Test add_note_to_memory
        result = _add_note_to_memory_impl(content="Test")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        
        # Test search_memory
        result = _search_memory_impl(query="test")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        
        # Test update_memory_entry
        result = _update_memory_entry_impl(entry_id=1, content="Updated")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        
        # Test delete_memory_entry
        result = _delete_memory_entry_impl(entry_id=1)
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        
        # Test list_all_memories
        result = _list_all_memories_impl()
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
        
        # Test get_project_rules
        result = _get_project_rules_impl()
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
    
    @patch('main.memory_service')
    def test_all_tools_handle_validation_errors(self, mock_service):
        """Test that all MCP tools properly handle validation errors"""
        mock_service.add_memory.side_effect = ValidationError("Invalid data", "content", "")
        mock_service.update_memory.side_effect = ValidationError("Invalid data", "content", "")
        
        # Test add_note_to_memory
        result = _add_note_to_memory_impl(content="Test")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        
        # Test update_memory_entry
        result = _update_memory_entry_impl(entry_id=1, content="Updated")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
    
    @patch('main.memory_service')
    def test_all_tools_handle_not_found_errors(self, mock_service):
        """Test that all MCP tools properly handle not found errors"""
        mock_service.update_memory.side_effect = NotFoundError("Entry not found", 999)
        mock_service.delete_memory.side_effect = NotFoundError("Entry not found", 999)
        
        # Test update_memory_entry
        result = _update_memory_entry_impl(entry_id=999, content="Updated")
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
        
        # Test delete_memory_entry
        result = _delete_memory_entry_impl(entry_id=999)
        assert "error" in result
        assert result["error"]["code"] == ErrorCodes.MCP_INVALID_PARAMS
    
    @patch('main.memory_service')
    def test_all_tools_handle_unexpected_errors(self, mock_service):
        """Test that all MCP tools properly handle unexpected errors"""
        mock_service.add_memory.side_effect = Exception("Unexpected error")
        mock_service.search_memories.side_effect = Exception("Unexpected error")
        mock_service.update_memory.side_effect = Exception("Unexpected error")
        mock_service.delete_memory.side_effect = Exception("Unexpected error")
        mock_service.list_all_memories.side_effect = Exception("Unexpected error")
        
        # Test all tools handle unexpected errors
        tools_and_params = [
            (_add_note_to_memory_impl, {"content": "Test"}),
            (_search_memory_impl, {"query": "test"}),
            (_update_memory_entry_impl, {"entry_id": 1, "content": "Updated"}),
            (_delete_memory_entry_impl, {"entry_id": 1}),
            (_list_all_memories_impl, {}),
            (_get_project_rules_impl, {})
        ]
        
        for tool_func, params in tools_and_params:
            result = tool_func(**params)
            assert "error" in result
            assert result["error"]["code"] == ErrorCodes.MCP_INTERNAL_ERROR
            assert "予期しないエラーが発生しました" in result["error"]["message"]


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])