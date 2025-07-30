#!/usr/bin/env python3
"""
Unit tests for MemoryService class
Tests all CRUD operations and search functionality using in-memory SQLite database
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime
from typing import List, Dict, Any

# Import the classes we need to test
from main import (
    MemoryService, 
    MemoryEntry, 
    NotFoundError, 
    ValidationError, 
    DatabaseError,
    MemoryServerError
)


class TestMemoryService:
    """Test suite for MemoryService class"""
    
    @pytest.fixture
    def memory_service(self):
        """Create a MemoryService instance with temporary database for testing"""
        # Use temporary file database for testing to ensure persistence during test
        import tempfile
        import os
        
        # Create a temporary file for the database
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)  # Close the file descriptor, we only need the path
        
        try:
            service = MemoryService(db_path)
            yield service
        finally:
            # Clean up the temporary database file
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.fixture
    def sample_memory_data(self):
        """Sample memory data for testing"""
        return {
            "content": "This is a test memory entry",
            "tags": ["test", "sample"],
            "keywords": ["memory", "testing"],
            "summary": "A test entry for unit testing"
        }
    
    @pytest.fixture
    def multiple_memory_entries(self, memory_service):
        """Create multiple memory entries for testing search and list operations"""
        entries_data = [
            {
                "content": "Python programming best practices",
                "tags": ["programming", "python", "rules"],
                "keywords": ["python", "best", "practices"],
                "summary": "Guidelines for Python development"
            },
            {
                "content": "Database design principles",
                "tags": ["database", "design", "rules"],
                "keywords": ["database", "design", "sql"],
                "summary": "Key principles for database design"
            },
            {
                "content": "API development guidelines",
                "tags": ["api", "development", "guidelines"],
                "keywords": ["api", "rest", "development"],
                "summary": "Best practices for API development"
            },
            {
                "content": "Testing strategies for Python applications",
                "tags": ["testing", "python", "knowledge"],
                "keywords": ["testing", "pytest", "unittest"],
                "summary": "Comprehensive testing approaches"
            }
        ]
        
        entry_ids = []
        for entry_data in entries_data:
            entry_id = memory_service.add_memory(**entry_data)
            entry_ids.append(entry_id)
        
        return entry_ids, entries_data


class TestMemoryServiceBasicOperations(TestMemoryService):
    """Test basic CRUD operations"""
    
    def test_add_memory_success(self, memory_service, sample_memory_data):
        """Test successful memory addition"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        
        assert isinstance(entry_id, int)
        assert entry_id > 0
    
    def test_add_memory_minimal_data(self, memory_service):
        """Test adding memory with minimal required data"""
        entry_id = memory_service.add_memory("Minimal content")
        
        assert isinstance(entry_id, int)
        assert entry_id > 0
        
        # Verify the entry was stored correctly
        retrieved = memory_service.get_memory_by_id(entry_id)
        assert retrieved["content"] == "Minimal content"
        assert retrieved["tags"] == []
        assert retrieved["keywords"] == []
        assert retrieved["summary"] == ""
    
    def test_add_memory_empty_content_fails(self, memory_service):
        """Test that adding memory with empty content fails"""
        with pytest.raises(ValidationError) as exc_info:
            memory_service.add_memory("")
        
        assert "Content cannot be empty" in str(exc_info.value)
    
    def test_add_memory_whitespace_content_fails(self, memory_service):
        """Test that adding memory with only whitespace content fails"""
        with pytest.raises(ValidationError) as exc_info:
            memory_service.add_memory("   \n\t   ")
        
        assert "Content cannot be empty" in str(exc_info.value)
    
    def test_add_memory_invalid_tags_fails(self, memory_service):
        """Test that adding memory with invalid tags fails"""
        with pytest.raises(ValidationError) as exc_info:
            memory_service.add_memory("Valid content", tags=["valid", "", "another"])
        
        assert "non-empty strings" in str(exc_info.value)
    
    def test_add_memory_invalid_keywords_fails(self, memory_service):
        """Test that adding memory with invalid keywords fails"""
        with pytest.raises(ValidationError) as exc_info:
            memory_service.add_memory("Valid content", keywords=["valid", None])
        
        assert "non-empty strings" in str(exc_info.value)


class TestMemoryServiceRetrieval(TestMemoryService):
    """Test memory retrieval operations"""
    
    def test_get_memory_by_id_success(self, memory_service, sample_memory_data):
        """Test successful memory retrieval by ID"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        retrieved = memory_service.get_memory_by_id(entry_id)
        
        assert retrieved["id"] == entry_id
        assert retrieved["content"] == sample_memory_data["content"]
        assert retrieved["tags"] == sample_memory_data["tags"]
        assert retrieved["keywords"] == sample_memory_data["keywords"]
        assert retrieved["summary"] == sample_memory_data["summary"]
        assert "created_at" in retrieved
        assert "updated_at" in retrieved
    
    def test_get_memory_by_id_not_found(self, memory_service):
        """Test retrieval of non-existent memory entry"""
        with pytest.raises(NotFoundError) as exc_info:
            memory_service.get_memory_by_id(999)
        
        assert "not found" in str(exc_info.value)
        assert exc_info.value.details["entry_id"] == 999
    
    def test_get_memory_by_id_invalid_id(self, memory_service):
        """Test retrieval with invalid ID types"""
        with pytest.raises(NotFoundError):
            memory_service.get_memory_by_id(-1)


class TestMemoryServiceUpdate(TestMemoryService):
    """Test memory update operations"""
    
    def test_update_memory_content_only(self, memory_service, sample_memory_data):
        """Test updating only the content of a memory entry"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        new_content = "Updated content"
        
        result = memory_service.update_memory(entry_id, content=new_content)
        assert result is True
        
        retrieved = memory_service.get_memory_by_id(entry_id)
        assert retrieved["content"] == new_content
        assert retrieved["tags"] == sample_memory_data["tags"]  # Should remain unchanged
        assert retrieved["keywords"] == sample_memory_data["keywords"]  # Should remain unchanged
    
    def test_update_memory_tags_only(self, memory_service, sample_memory_data):
        """Test updating only the tags of a memory entry"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        new_tags = ["updated", "tags"]
        
        result = memory_service.update_memory(entry_id, tags=new_tags)
        assert result is True
        
        retrieved = memory_service.get_memory_by_id(entry_id)
        assert retrieved["tags"] == new_tags
        assert retrieved["content"] == sample_memory_data["content"]  # Should remain unchanged
    
    def test_update_memory_all_fields(self, memory_service, sample_memory_data):
        """Test updating all fields of a memory entry"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        
        updated_data = {
            "content": "Completely updated content",
            "tags": ["new", "updated", "tags"],
            "keywords": ["new", "keywords"],
            "summary": "Updated summary"
        }
        
        result = memory_service.update_memory(entry_id, **updated_data)
        assert result is True
        
        retrieved = memory_service.get_memory_by_id(entry_id)
        assert retrieved["content"] == updated_data["content"]
        assert retrieved["tags"] == updated_data["tags"]
        assert retrieved["keywords"] == updated_data["keywords"]
        assert retrieved["summary"] == updated_data["summary"]
    
    def test_update_memory_not_found(self, memory_service):
        """Test updating non-existent memory entry"""
        with pytest.raises(NotFoundError) as exc_info:
            memory_service.update_memory(999, content="New content")
        
        assert "not found" in str(exc_info.value)
        assert exc_info.value.details["entry_id"] == 999
    
    def test_update_memory_empty_content_fails(self, memory_service, sample_memory_data):
        """Test that updating with empty content fails"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        
        with pytest.raises(ValidationError) as exc_info:
            memory_service.update_memory(entry_id, content="")
        
        assert "Content cannot be empty" in str(exc_info.value)
    
    def test_update_memory_invalid_tags_fails(self, memory_service, sample_memory_data):
        """Test that updating with invalid tags fails"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        
        with pytest.raises(ValidationError) as exc_info:
            memory_service.update_memory(entry_id, tags=["valid", ""])
        
        assert "non-empty strings" in str(exc_info.value)


class TestMemoryServiceDeletion(TestMemoryService):
    """Test memory deletion operations"""
    
    def test_delete_memory_success(self, memory_service, sample_memory_data):
        """Test successful memory deletion"""
        entry_id = memory_service.add_memory(**sample_memory_data)
        
        # Verify entry exists
        retrieved = memory_service.get_memory_by_id(entry_id)
        assert retrieved["id"] == entry_id
        
        # Delete the entry
        result = memory_service.delete_memory(entry_id)
        assert result is True
        
        # Verify entry no longer exists
        with pytest.raises(NotFoundError):
            memory_service.get_memory_by_id(entry_id)
    
    def test_delete_memory_not_found(self, memory_service):
        """Test deletion of non-existent memory entry"""
        with pytest.raises(NotFoundError) as exc_info:
            memory_service.delete_memory(999)
        
        assert "not found" in str(exc_info.value)
        assert exc_info.value.details["entry_id"] == 999


class TestMemoryServiceSearch(TestMemoryService):
    """Test memory search operations"""
    
    def test_search_memories_by_content(self, memory_service, multiple_memory_entries):
        """Test searching memories by content keywords"""
        entry_ids, entries_data = multiple_memory_entries
        
        # Search for "python" in content
        results = memory_service.search_memories(query="python")
        
        assert len(results) == 2  # Should find 2 entries with "python"
        contents = [result["content"] for result in results]
        assert any("Python programming" in content for content in contents)
        assert any("Testing strategies for Python" in content for content in contents)
    
    def test_search_memories_by_tags(self, memory_service, multiple_memory_entries):
        """Test searching memories by tags"""
        entry_ids, entries_data = multiple_memory_entries
        
        # Search for entries with "rules" tag
        results = memory_service.search_memories(tags=["rules"])
        
        assert len(results) == 2  # Should find 2 entries with "rules" tag
        for result in results:
            assert "rules" in result["tags"]
    
    def test_search_memories_by_query_and_tags(self, memory_service, multiple_memory_entries):
        """Test searching memories by both query and tags"""
        entry_ids, entries_data = multiple_memory_entries
        
        # Search for "python" content with "rules" tag
        results = memory_service.search_memories(query="python", tags=["rules"])
        
        assert len(results) == 1  # Should find 1 entry matching both criteria
        assert "Python programming" in results[0]["content"]
        assert "rules" in results[0]["tags"]
    
    def test_search_memories_no_results(self, memory_service, multiple_memory_entries):
        """Test search with no matching results"""
        entry_ids, entries_data = multiple_memory_entries
        
        results = memory_service.search_memories(query="nonexistent")
        assert len(results) == 0
    
    def test_search_memories_with_limit(self, memory_service, multiple_memory_entries):
        """Test search with result limit"""
        entry_ids, entries_data = multiple_memory_entries
        
        # Search with limit of 2
        results = memory_service.search_memories(limit=2)
        assert len(results) == 2
    
    def test_search_memories_empty_query(self, memory_service, multiple_memory_entries):
        """Test search with empty query returns all entries"""
        entry_ids, entries_data = multiple_memory_entries
        
        results = memory_service.search_memories(query="")
        assert len(results) == 4  # Should return all entries
    
    def test_search_memories_case_insensitive(self, memory_service, multiple_memory_entries):
        """Test that search is case insensitive"""
        entry_ids, entries_data = multiple_memory_entries
        
        results_lower = memory_service.search_memories(query="python")
        results_upper = memory_service.search_memories(query="PYTHON")
        results_mixed = memory_service.search_memories(query="Python")
        
        assert len(results_lower) == len(results_upper) == len(results_mixed)
        assert len(results_lower) > 0


class TestMemoryServiceListAll(TestMemoryService):
    """Test list all memories operations"""
    
    def test_list_all_memories_success(self, memory_service, multiple_memory_entries):
        """Test listing all memory entries"""
        entry_ids, entries_data = multiple_memory_entries
        
        results = memory_service.list_all_memories()
        
        assert len(results) == 4
        
        # Verify metadata is included
        for result in results:
            assert "metadata" in result
            assert "tag_count" in result["metadata"]
            assert "keyword_count" in result["metadata"]
            assert "content_length" in result["metadata"]
            assert "has_summary" in result["metadata"]
    
    def test_list_all_memories_with_limit(self, memory_service, multiple_memory_entries):
        """Test listing memories with limit"""
        entry_ids, entries_data = multiple_memory_entries
        
        results = memory_service.list_all_memories(limit=2)
        assert len(results) == 2
    
    def test_list_all_memories_empty_database(self, memory_service):
        """Test listing memories from empty database"""
        results = memory_service.list_all_memories()
        assert len(results) == 0
    
    def test_list_all_memories_ordered_by_recent(self, memory_service):
        """Test that memories are ordered by most recent first"""
        # Add entries with slight delay to ensure different timestamps
        import time
        
        first_id = memory_service.add_memory("First entry")
        time.sleep(0.01)  # Small delay
        second_id = memory_service.add_memory("Second entry")
        time.sleep(0.01)  # Small delay
        third_id = memory_service.add_memory("Third entry")
        
        results = memory_service.list_all_memories()
        
        # Should be ordered by most recent first
        assert results[0]["content"] == "Third entry"
        assert results[1]["content"] == "Second entry"
        assert results[2]["content"] == "First entry"


class TestMemoryServiceDatabaseOperations(TestMemoryService):
    """Test database-specific operations and edge cases"""
    
    def test_database_initialization(self):
        """Test that database is properly initialized"""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Initialize service with file database
            service = MemoryService(db_path)
            
            # Verify tables exist
            with service.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='memory_entries'
                """)
                result = cursor.fetchone()
                assert result is not None
                
                # Verify indexes exist
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name LIKE 'idx_memory_%'
                """)
                indexes = cursor.fetchall()
                assert len(indexes) >= 4  # Should have at least 4 indexes
        
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_database_connection_properties(self, memory_service):
        """Test database connection properties"""
        with memory_service.get_connection() as conn:
            # Test row factory is set
            assert conn.row_factory == sqlite3.Row
            
            # Test foreign keys are enabled
            cursor = conn.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            assert result[0] == 1  # Foreign keys should be enabled
    
    def test_concurrent_operations(self, memory_service):
        """Test that concurrent operations work correctly"""
        # Add multiple entries
        entry_ids = []
        for i in range(5):
            entry_id = memory_service.add_memory(f"Entry {i}", tags=[f"tag{i}"])
            entry_ids.append(entry_id)
        
        # Perform concurrent-like operations
        for entry_id in entry_ids:
            retrieved = memory_service.get_memory_by_id(entry_id)
            assert retrieved["id"] == entry_id
        
        # Update all entries
        for i, entry_id in enumerate(entry_ids):
            memory_service.update_memory(entry_id, content=f"Updated Entry {i}")
        
        # Verify all updates
        for i, entry_id in enumerate(entry_ids):
            retrieved = memory_service.get_memory_by_id(entry_id)
            assert retrieved["content"] == f"Updated Entry {i}"


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])