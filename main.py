#!/usr/bin/env python3
"""
Memory Server MCP - Personal memory server for Cursor/Claude integration
Provides long-term memory functionality through MCP protocol and REST API
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import json

from fastapi import FastAPI, HTTPException
from fastmcp import FastMCP
import uvicorn

# Configuration class with enhanced settings
class Config:
    """Configuration management for the memory server"""
    import os
    
    # Default values
    DATABASE_PATH = os.getenv("MEMORY_DB_PATH", "memory.db")
    HOST = os.getenv("MEMORY_SERVER_HOST", "localhost")
    PORT = int(os.getenv("MEMORY_SERVER_PORT", "8000"))
    LOG_LEVEL = os.getenv("MEMORY_LOG_LEVEL", "INFO").upper()
    MAX_SEARCH_RESULTS = int(os.getenv("MEMORY_MAX_SEARCH_RESULTS", "100"))
    LOG_FILE = os.getenv("MEMORY_LOG_FILE", "memory_server.log")
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Validate configuration
    @classmethod
    def validate_config(cls):
        """Validate configuration values"""
        if cls.PORT < 1 or cls.PORT > 65535:
            raise ValueError(f"Invalid port number: {cls.PORT}")
        
        if cls.MAX_SEARCH_RESULTS < 1 or cls.MAX_SEARCH_RESULTS > 1000:
            raise ValueError(f"Invalid max search results: {cls.MAX_SEARCH_RESULTS}")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL not in valid_log_levels:
            raise ValueError(f"Invalid log level: {cls.LOG_LEVEL}. Must be one of {valid_log_levels}")
        
        return True
    
    @classmethod
    def setup_logging(cls):
        """Setup logging configuration with proper handlers and formatters"""
        # Create formatter
        formatter = logging.Formatter(cls.LOG_FORMAT)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, cls.LOG_LEVEL.upper()))
        
        # Clear existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(cls.LOG_FILE, encoding='utf-8')
        file_handler.setLevel(getattr(logging, cls.LOG_LEVEL.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, cls.LOG_LEVEL.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Set specific logger levels for third-party libraries
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("fastapi").setLevel(logging.WARNING)
        
        return logging.getLogger(__name__)

# Validate and initialize configuration
try:
    Config.validate_config()
    logger = Config.setup_logging()
    logger.info("Configuration validated and logging initialized")
except Exception as e:
    print(f"Configuration error: {e}")
    raise

# Custom exceptions
class MemoryServerError(Exception):
    """Base exception for memory server errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class NotFoundError(MemoryServerError):
    """Raised when a memory entry is not found"""
    def __init__(self, message: str, entry_id: int = None):
        details = {"entry_id": entry_id} if entry_id is not None else {}
        super().__init__(message, details)

class ValidationError(MemoryServerError):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)
        super().__init__(message, details)

class DatabaseError(MemoryServerError):
    """Raised when database operations fail"""
    def __init__(self, message: str, operation: str = None):
        details = {"operation": operation} if operation is not None else {}
        super().__init__(message, details)

class MCPError(MemoryServerError):
    """Raised when MCP protocol operations fail"""
    def __init__(self, message: str, code: int = -32603, data: Dict[str, Any] = None):
        self.code = code
        self.data = data or {}
        super().__init__(message, self.data)



# Error response utilities
class ErrorResponse:
    """Utility class for creating standardized error responses"""
    
    @staticmethod
    def create_error_response(error_code: str, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized error response for REST API"""
        return {
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {}
            }
        }
    
    @staticmethod
    def create_mcp_error_response(code: int, message: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized error response for MCP protocol"""
        return {
            "error": {
                "code": code,
                "message": message,
                "data": data or {}
            }
        }
    
    @staticmethod
    def log_error(error: Exception, context: str = "", extra_data: Dict[str, Any] = None):
        """Log error with standardized format and context"""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        
        if extra_data:
            error_data.update(extra_data)
        
        if isinstance(error, MemoryServerError):
            error_data["details"] = getattr(error, 'details', {})
        
        logger.error(f"Error in {context}: {error_data}")
        
        # Log stack trace for unexpected errors
        if not isinstance(error, (NotFoundError, ValidationError)):
            logger.exception(f"Stack trace for error in {context}")

# Error code constants
class ErrorCodes:
    """Constants for error codes"""
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    MCP_PROTOCOL_ERROR = "MCP_PROTOCOL_ERROR"
    
    # MCP error codes (JSON-RPC 2.0 standard)
    MCP_PARSE_ERROR = -32700
    MCP_INVALID_REQUEST = -32600
    MCP_METHOD_NOT_FOUND = -32601
    MCP_INVALID_PARAMS = -32602
    MCP_INTERNAL_ERROR = -32603

# Initialize FastAPI app
app = FastAPI(
    title="Memory Server MCP",
    description="Personal memory server for Cursor/Claude integration",
    version="1.0.0"
)

# Initialize FastMCP with proper configuration
mcp = FastMCP("Memory Server")

# FastAPI error handlers
@app.exception_handler(NotFoundError)
async def not_found_error_handler(request, exc: NotFoundError):
    """Handle NotFoundError exceptions"""
    ErrorResponse.log_error(exc, "API request", {"request_url": str(request.url)})
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=404,
        content=ErrorResponse.create_error_response(
            ErrorCodes.MEMORY_NOT_FOUND,
            exc.message,
            exc.details
        )
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Handle ValidationError exceptions"""
    ErrorResponse.log_error(exc, "API request", {"request_url": str(request.url)})
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=400,
        content=ErrorResponse.create_error_response(
            ErrorCodes.VALIDATION_ERROR,
            exc.message,
            exc.details
        )
    )

@app.exception_handler(DatabaseError)
async def database_error_handler(request, exc: DatabaseError):
    """Handle DatabaseError exceptions"""
    ErrorResponse.log_error(exc, "API request", {"request_url": str(request.url)})
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content=ErrorResponse.create_error_response(
            ErrorCodes.DATABASE_ERROR,
            "データベース操作中にエラーが発生しました",
            exc.details
        )
    )

@app.exception_handler(MemoryServerError)
async def memory_server_error_handler(request, exc: MemoryServerError):
    """Handle general MemoryServerError exceptions"""
    ErrorResponse.log_error(exc, "API request", {"request_url": str(request.url)})
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content=ErrorResponse.create_error_response(
            ErrorCodes.INTERNAL_ERROR,
            exc.message,
            exc.details
        )
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions"""
    ErrorResponse.log_error(exc, "API request", {"request_url": str(request.url)})
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content=ErrorResponse.create_error_response(
            ErrorCodes.INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(exc).__name__}
        )
    )

@dataclass
class MemoryEntry:
    """Data class representing a memory entry"""
    id: Optional[int]
    content: str
    tags: List[str]
    keywords: List[str]
    summary: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Ensure tags and keywords are lists
        if self.tags is None:
            self.tags = []
        if self.keywords is None:
            self.keywords = []
        if self.summary is None:
            self.summary = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses"""
        return {
            "id": self.id,
            "content": self.content,
            "tags": self.tags,
            "keywords": self.keywords,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for database storage"""
        return {
            "content": self.content,
            "tags": json.dumps(self.tags, ensure_ascii=False),
            "keywords": json.dumps(self.keywords, ensure_ascii=False),
            "summary": self.summary or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary (API input)"""
        return cls(
            id=data.get("id"),
            content=data["content"],
            tags=data.get("tags", []),
            keywords=data.get("keywords", []),
            summary=data.get("summary", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )
    
    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> 'MemoryEntry':
        """Create from database row"""
        return cls(
            id=row["id"],
            content=row["content"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            summary=row["summary"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        )
    
    def validate(self) -> bool:
        """Validate the memory entry data"""
        if not self.content or not self.content.strip():
            raise ValidationError("Content cannot be empty", "content", self.content)
        
        if not isinstance(self.tags, list):
            raise ValidationError("Tags must be a list", "tags", type(self.tags).__name__)
        
        if not isinstance(self.keywords, list):
            raise ValidationError("Keywords must be a list", "keywords", type(self.keywords).__name__)
        
        # Validate tag and keyword content
        for i, tag in enumerate(self.tags):
            if not isinstance(tag, str) or not tag.strip():
                raise ValidationError(f"All tags must be non-empty strings", f"tags[{i}]", tag)
        
        for i, keyword in enumerate(self.keywords):
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValidationError(f"All keywords must be non-empty strings", f"keywords[{i}]", keyword)
        
        return True

class MemoryService:
    """Service class for memory operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints and set row factory
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            
            # Create main memory_entries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    tags TEXT,  -- JSON array format
                    keywords TEXT,  -- JSON array format
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better search performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory_entries(tags)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_keywords ON memory_entries(keywords)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory_entries(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_updated_at ON memory_entries(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_content ON memory_entries(content)")
            
            # Create trigger to automatically update updated_at timestamp
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_memory_timestamp 
                AFTER UPDATE ON memory_entries
                FOR EACH ROW
                BEGIN
                    UPDATE memory_entries 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END
            """)
            
            conn.commit()
            logger.info("Database initialized successfully with schema and indexes")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def add_memory(self, content: str, tags: List[str] = None, 
                   keywords: List[str] = None, summary: str = None) -> int:
        """Add a new memory entry to the database"""
        try:
            # Create memory entry and validate
            memory_entry = MemoryEntry(
                id=None,
                content=content,
                tags=tags or [],
                keywords=keywords or [],
                summary=summary or "",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            memory_entry.validate()
            
            # Convert to database format
            db_data = memory_entry.to_db_dict()
            
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO memory_entries (content, tags, keywords, summary, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    db_data["content"],
                    db_data["tags"],
                    db_data["keywords"],
                    db_data["summary"],
                    db_data["created_at"],
                    db_data["updated_at"]
                ))
                
                entry_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Added memory entry with ID: {entry_id}")
                return entry_id
                
        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except ValueError as e:
            ErrorResponse.log_error(e, "add_memory", {"content_length": len(content)})
            raise ValidationError(f"Invalid memory data: {e}")
        except sqlite3.Error as e:
            ErrorResponse.log_error(e, "add_memory", {"operation": "database_insert"})
            raise DatabaseError(f"Failed to add memory entry: {e}", "insert")
        except Exception as e:
            ErrorResponse.log_error(e, "add_memory", {"content_length": len(content)})
            raise MemoryServerError(f"Failed to add memory entry: {e}")
    
    def get_memory_by_id(self, entry_id: int) -> Dict[str, Any]:
        """Get a memory entry by its ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM memory_entries WHERE id = ?",
                    (entry_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise NotFoundError(f"Memory entry with ID {entry_id} not found", entry_id)
                
                memory_entry = MemoryEntry.from_db_row(row)
                logger.info(f"Retrieved memory entry with ID: {entry_id}")
                return memory_entry.to_dict()
                
        except NotFoundError:
            raise
        except sqlite3.Error as e:
            ErrorResponse.log_error(e, "get_memory_by_id", {"entry_id": entry_id, "operation": "database_select"})
            raise DatabaseError(f"Failed to retrieve memory entry: {e}", "select")
        except Exception as e:
            ErrorResponse.log_error(e, "get_memory_by_id", {"entry_id": entry_id})
            raise MemoryServerError(f"Failed to retrieve memory entry: {e}")
    
    def update_memory(self, entry_id: int, content: str = None, 
                     tags: List[str] = None, keywords: List[str] = None, 
                     summary: str = None) -> bool:
        """Update an existing memory entry"""
        try:
            # First check if the entry exists
            existing_entry = self.get_memory_by_id(entry_id)
            
            # Prepare update data - use existing values if new ones not provided
            update_content = content if content is not None else existing_entry["content"]
            update_tags = tags if tags is not None else existing_entry["tags"]
            update_keywords = keywords if keywords is not None else existing_entry["keywords"]
            update_summary = summary if summary is not None else existing_entry["summary"]
            
            # Create updated memory entry and validate
            updated_entry = MemoryEntry(
                id=entry_id,
                content=update_content,
                tags=update_tags,
                keywords=update_keywords,
                summary=update_summary,
                created_at=datetime.fromisoformat(existing_entry["created_at"]),
                updated_at=datetime.now()
            )
            updated_entry.validate()
            
            # Convert to database format
            db_data = updated_entry.to_db_dict()
            
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE memory_entries 
                    SET content = ?, tags = ?, keywords = ?, summary = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    db_data["content"],
                    db_data["tags"],
                    db_data["keywords"],
                    db_data["summary"],
                    db_data["updated_at"],
                    entry_id
                ))
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Memory entry with ID {entry_id} not found", entry_id)
                
                conn.commit()
                logger.info(f"Updated memory entry with ID: {entry_id}")
                return True
                
        except (NotFoundError, ValidationError):
            # Re-raise these exceptions as-is
            raise
        except sqlite3.Error as e:
            ErrorResponse.log_error(e, "update_memory", {"entry_id": entry_id, "operation": "database_update"})
            raise DatabaseError(f"Failed to update memory entry: {e}", "update")
        except Exception as e:
            ErrorResponse.log_error(e, "update_memory", {"entry_id": entry_id})
            raise MemoryServerError(f"Failed to update memory entry: {e}")
    
    def delete_memory(self, entry_id: int) -> bool:
        """Delete a memory entry by its ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM memory_entries WHERE id = ?",
                    (entry_id,)
                )
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Memory entry with ID {entry_id} not found", entry_id)
                
                conn.commit()
                logger.info(f"Deleted memory entry with ID: {entry_id}")
                return True
                
        except NotFoundError:
            raise
        except sqlite3.Error as e:
            ErrorResponse.log_error(e, "delete_memory", {"entry_id": entry_id, "operation": "database_delete"})
            raise DatabaseError(f"Failed to delete memory entry: {e}", "delete")
        except Exception as e:
            ErrorResponse.log_error(e, "delete_memory", {"entry_id": entry_id})
            raise MemoryServerError(f"Failed to delete memory entry: {e}")
    
    def search_memories(self, query: str = None, tags: List[str] = None, 
                       limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory entries by keyword query and/or tags"""
        try:
            # Validate limit
            if limit <= 0 or limit > Config.MAX_SEARCH_RESULTS:
                limit = Config.MAX_SEARCH_RESULTS
            
            # Build SQL query based on search parameters
            sql_conditions = []
            sql_params = []
            
            # Add keyword search condition
            if query and query.strip():
                # Search in content, summary, tags, and keywords
                sql_conditions.append("""
                    (content LIKE ? OR summary LIKE ? OR tags LIKE ? OR keywords LIKE ?)
                """)
                search_term = f"%{query.strip()}%"
                sql_params.extend([search_term, search_term, search_term, search_term])
            
            # Add tag search condition
            if tags and len(tags) > 0:
                # Search for any of the specified tags
                tag_conditions = []
                for tag in tags:
                    if tag.strip():
                        tag_conditions.append("tags LIKE ?")
                        sql_params.append(f'%"{tag.strip()}"%')
                
                if tag_conditions:
                    sql_conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # Build final SQL query
            base_query = "SELECT * FROM memory_entries"
            if sql_conditions:
                base_query += " WHERE " + " AND ".join(sql_conditions)
            
            base_query += " ORDER BY updated_at DESC, created_at DESC LIMIT ?"
            sql_params.append(limit)
            
            with self.get_connection() as conn:
                cursor = conn.execute(base_query, sql_params)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    memory_entry = MemoryEntry.from_db_row(row)
                    results.append(memory_entry.to_dict())
                
                logger.info(f"Search completed: found {len(results)} entries (query='{query}', tags={tags})")
                return results
                
        except sqlite3.Error as e:
            ErrorResponse.log_error(e, "search_memories", {"query": query, "tags": tags, "operation": "database_search"})
            raise DatabaseError(f"Failed to search memory entries: {e}", "search")
        except Exception as e:
            ErrorResponse.log_error(e, "search_memories", {"query": query, "tags": tags})
            raise MemoryServerError(f"Failed to search memory entries: {e}")
    
    def list_all_memories(self, limit: int = None) -> List[Dict[str, Any]]:
        """List all memory entries with metadata, ordered by most recent first"""
        try:
            # Set default limit if not provided
            if limit is None:
                limit = Config.MAX_SEARCH_RESULTS
            elif limit <= 0 or limit > Config.MAX_SEARCH_RESULTS:
                limit = Config.MAX_SEARCH_RESULTS
            
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM memory_entries 
                    ORDER BY updated_at DESC, created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    memory_entry = MemoryEntry.from_db_row(row)
                    # Include additional metadata for listing
                    entry_dict = memory_entry.to_dict()
                    entry_dict["metadata"] = {
                        "tag_count": len(memory_entry.tags),
                        "keyword_count": len(memory_entry.keywords),
                        "content_length": len(memory_entry.content),
                        "has_summary": bool(memory_entry.summary and memory_entry.summary.strip())
                    }
                    results.append(entry_dict)
                
                logger.info(f"Listed {len(results)} memory entries")
                return results
                
        except sqlite3.Error as e:
            ErrorResponse.log_error(e, "list_all_memories", {"limit": limit, "operation": "database_list"})
            raise DatabaseError(f"Failed to list memory entries: {e}", "list")
        except Exception as e:
            ErrorResponse.log_error(e, "list_all_memories", {"limit": limit})
            raise MemoryServerError(f"Failed to list memory entries: {e}")

# Initialize memory service
memory_service = MemoryService(Config.DATABASE_PATH)

# MCP error handling utilities
def handle_mcp_error(func):
    """Decorator to handle errors in MCP tool functions"""
    import functools
    
    @functools.wraps(func)
    def wrapper(**kwargs):
        try:
            return func(**kwargs)
        except NotFoundError as e:
            ErrorResponse.log_error(e, f"MCP tool: {func.__name__}")
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INVALID_PARAMS,
                e.message,
                e.details
            )
        except ValidationError as e:
            ErrorResponse.log_error(e, f"MCP tool: {func.__name__}")
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INVALID_PARAMS,
                e.message,
                e.details
            )
        except DatabaseError as e:
            ErrorResponse.log_error(e, f"MCP tool: {func.__name__}")
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INTERNAL_ERROR,
                "データベース操作中にエラーが発生しました",
                e.details
            )
        except MCPError as e:
            ErrorResponse.log_error(e, f"MCP tool: {func.__name__}")
            return ErrorResponse.create_mcp_error_response(
                e.code,
                e.message,
                e.data
            )
        except Exception as e:
            ErrorResponse.log_error(e, f"MCP tool: {func.__name__}")
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INTERNAL_ERROR,
                "予期しないエラーが発生しました",
                {"error_type": type(e).__name__}
            )
    return wrapper

# MCP server initialization and error handling
def initialize_mcp_server():
    """Initialize MCP server with proper error handling"""
    logger.info("Initializing MCP server with tools...")
    
    # Verify database connection
    try:
        with memory_service.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM memory_entries")
            count = cursor.fetchone()[0]
            logger.info(f"Database connection verified: {count} memory entries found")
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise
    
    logger.info("MCP server initialization completed")
    return True

# MCP protocol error handling utility
def handle_mcp_protocol_error(error, context="MCP operation"):
    """Handle MCP protocol-level errors with standardized responses"""
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context
    }
    
    ErrorResponse.log_error(error, "MCP protocol", error_context)
    
    # Return standardized MCP error response
    if isinstance(error, ValueError):
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            "Invalid parameters provided",
            error_context
        )
    elif isinstance(error, KeyError):
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_REQUEST,
            "Required parameter missing",
            error_context
        )
    else:
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "Internal server error",
            error_context
        )

# Basic health check endpoint
@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "message": "Memory Server MCP is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }

# MCP Tools Implementation

def _add_note_to_memory_impl(
    content: str,
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    summary: Optional[str] = None
) -> dict:
    """
    メモリにノートを追加する実装
    """
    try:
        # Input validation
        if not content or not content.strip():
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INVALID_PARAMS,
                "Content cannot be empty",
                {"field": "content", "invalid_value": content}
            )
        
        # Add memory entry
        entry_id = memory_service.add_memory(
            content=content.strip(),
            tags=tags or [],
            keywords=keywords or [],
            summary=summary.strip() if summary else None
        )
        
        # Return the created entry
        created_entry = memory_service.get_memory_by_id(entry_id)
        
        logger.info(f"MCP: Added memory entry with ID {entry_id}")
        return {
            "success": True,
            "message": f"メモリエントリが正常に追加されました (ID: {entry_id})",
            "entry": created_entry
        }
        
    except NotFoundError as e:
        ErrorResponse.log_error(e, "MCP tool: add_note_to_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except ValidationError as e:
        ErrorResponse.log_error(e, "MCP tool: add_note_to_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except DatabaseError as e:
        ErrorResponse.log_error(e, "MCP tool: add_note_to_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "データベース操作中にエラーが発生しました",
            e.details
        )
    except Exception as e:
        ErrorResponse.log_error(e, "MCP tool: add_note_to_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(e).__name__}
        )

def _search_memory_impl(
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10
) -> dict:
    """
    キーワードまたはタグでメモリを検索する実装
    """
    try:
        # Input validation
        if limit <= 0 or limit > Config.MAX_SEARCH_RESULTS:
            limit = 10
        
        # Perform search
        results = memory_service.search_memories(
            query=query.strip() if query else None,
            tags=[tag.strip() for tag in tags if tag.strip()] if tags else None,
            limit=limit
        )
        
        logger.info(f"MCP: Search completed, found {len(results)} entries")
        return {
            "success": True,
            "message": f"{len(results)}件のメモリエントリが見つかりました",
            "results": results,
            "search_params": {
                "query": query,
                "tags": tags,
                "limit": limit
            }
        }
        
    except NotFoundError as e:
        ErrorResponse.log_error(e, "MCP tool: search_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except ValidationError as e:
        ErrorResponse.log_error(e, "MCP tool: search_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except DatabaseError as e:
        ErrorResponse.log_error(e, "MCP tool: search_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "データベース操作中にエラーが発生しました",
            e.details
        )
    except Exception as e:
        ErrorResponse.log_error(e, "MCP tool: search_memory")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(e).__name__}
        )

@mcp.tool()
def add_note_to_memory(
    content: str,
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    summary: Optional[str] = None
) -> dict:
    """
    メモリにノートを追加する
    
    Args:
        content (str): メモリエントリの内容（必須）
        tags (List[str], optional): タグのリスト（例: ["ルール", "決定事項", "知識"]）
        keywords (List[str], optional): キーワードのリスト
        summary (str, optional): 短い要約
    
    Returns:
        dict: 作成されたメモリエントリの情報
    """
    return _add_note_to_memory_impl(content, tags, keywords, summary)

@mcp.tool()
def search_memory(
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10
) -> dict:
    """
    キーワードまたはタグでメモリを検索する
    
    Args:
        query (str, optional): 検索クエリ（内容、要約、タグ、キーワードから検索）
        tags (List[str], optional): 検索対象のタグリスト
        limit (int): 返す結果の最大数（デフォルト: 10）
    
    Returns:
        dict: 検索結果のメモリエントリリスト
    """
    return _search_memory_impl(query, tags, limit)

def _update_memory_entry_impl(
    entry_id: int,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    summary: Optional[str] = None
) -> dict:
    """
    既存のメモリエントリを更新する実装
    """
    try:
        # Input validation
        if not isinstance(entry_id, int) or entry_id <= 0:
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INVALID_PARAMS,
                "Entry ID must be a positive integer",
                {"field": "entry_id", "invalid_value": entry_id}
            )
        
        # Update memory entry
        success = memory_service.update_memory(
            entry_id=entry_id,
            content=content.strip() if content else None,
            tags=tags,
            keywords=keywords,
            summary=summary.strip() if summary else None
        )
        
        if success:
            # Return the updated entry
            updated_entry = memory_service.get_memory_by_id(entry_id)
            
            logger.info(f"MCP: Updated memory entry with ID {entry_id}")
            return {
                "success": True,
                "message": f"メモリエントリが正常に更新されました (ID: {entry_id})",
                "entry": updated_entry
            }
        else:
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INVALID_PARAMS,
                f"Failed to update memory entry with ID {entry_id}",
                {"entry_id": entry_id}
            )
        
    except NotFoundError as e:
        ErrorResponse.log_error(e, "MCP tool: update_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except ValidationError as e:
        ErrorResponse.log_error(e, "MCP tool: update_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except DatabaseError as e:
        ErrorResponse.log_error(e, "MCP tool: update_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "データベース操作中にエラーが発生しました",
            e.details
        )
    except Exception as e:
        ErrorResponse.log_error(e, "MCP tool: update_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(e).__name__}
        )

def _delete_memory_entry_impl(entry_id: int) -> dict:
    """
    メモリエントリを削除する実装
    """
    try:
        # Input validation
        if not isinstance(entry_id, int) or entry_id <= 0:
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INVALID_PARAMS,
                "Entry ID must be a positive integer",
                {"field": "entry_id", "invalid_value": entry_id}
            )
        
        # Delete memory entry
        success = memory_service.delete_memory(entry_id)
        
        if success:
            logger.info(f"MCP: Deleted memory entry with ID {entry_id}")
            return {
                "success": True,
                "message": f"メモリエントリが正常に削除されました (ID: {entry_id})",
                "deleted_entry_id": entry_id
            }
        else:
            return ErrorResponse.create_mcp_error_response(
                ErrorCodes.MCP_INVALID_PARAMS,
                f"Failed to delete memory entry with ID {entry_id}",
                {"entry_id": entry_id}
            )
        
    except NotFoundError as e:
        ErrorResponse.log_error(e, "MCP tool: delete_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except ValidationError as e:
        ErrorResponse.log_error(e, "MCP tool: delete_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except DatabaseError as e:
        ErrorResponse.log_error(e, "MCP tool: delete_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "データベース操作中にエラーが発生しました",
            e.details
        )
    except Exception as e:
        ErrorResponse.log_error(e, "MCP tool: delete_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(e).__name__}
        )
    except NotFoundError as e:
        ErrorResponse.log_error(e, "MCP tool: delete_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INVALID_PARAMS,
            e.message,
            e.details
        )
    except DatabaseError as e:
        ErrorResponse.log_error(e, "MCP tool: delete_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "データベース操作中にエラーが発生しました",
            e.details
        )
    except Exception as e:
        ErrorResponse.log_error(e, "MCP tool: delete_memory_entry")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(e).__name__}
        )

def _list_all_memories_impl(limit: int = 50) -> dict:
    """
    すべてのメモリエントリをメタデータと共に一覧表示する実装
    """
    try:
        # Input validation
        if limit <= 0 or limit > Config.MAX_SEARCH_RESULTS:
            limit = 50
        
        # Get all memory entries
        results = memory_service.list_all_memories(limit=limit)
        
        logger.info(f"MCP: Listed {len(results)} memory entries")
        return {
            "success": True,
            "message": f"{len(results)}件のメモリエントリを取得しました",
            "entries": results,
            "total_count": len(results),
            "limit": limit
        }
        
    except DatabaseError as e:
        ErrorResponse.log_error(e, "MCP tool: list_all_memories")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "データベース操作中にエラーが発生しました",
            e.details
        )
    except Exception as e:
        ErrorResponse.log_error(e, "MCP tool: list_all_memories")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(e).__name__}
        )

def _get_project_rules_impl() -> dict:
    """
    プロジェクトルールタグ付きメモリを取得する実装
    """
    try:
        # Search for entries with "ルール" or "rule" tags
        rule_tags = ["ルール", "rule", "rules", "規則", "原則", "方針"]
        results = memory_service.search_memories(
            query=None,
            tags=rule_tags,
            limit=Config.MAX_SEARCH_RESULTS
        )
        
        logger.info(f"MCP: Retrieved {len(results)} project rule entries")
        return {
            "success": True,
            "message": f"{len(results)}件のプロジェクトルールが見つかりました",
            "rules": results,
            "rule_tags_searched": rule_tags
        }
        
    except DatabaseError as e:
        ErrorResponse.log_error(e, "MCP tool: get_project_rules")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "データベース操作中にエラーが発生しました",
            e.details
        )
    except Exception as e:
        ErrorResponse.log_error(e, "MCP tool: get_project_rules")
        return ErrorResponse.create_mcp_error_response(
            ErrorCodes.MCP_INTERNAL_ERROR,
            "予期しないエラーが発生しました",
            {"error_type": type(e).__name__}
        )

@mcp.tool()
def update_memory_entry(
    entry_id: int,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    summary: Optional[str] = None
) -> dict:
    """
    既存のメモリエントリを更新する
    
    Args:
        entry_id (int): 更新するメモリエントリのID
        content (str, optional): 新しい内容
        tags (List[str], optional): 新しいタグリスト
        keywords (List[str], optional): 新しいキーワードリスト
        summary (str, optional): 新しい要約
    
    Returns:
        dict: 更新されたメモリエントリの情報
    """
    return _update_memory_entry_impl(entry_id, content, tags, keywords, summary)

@mcp.tool()
def delete_memory_entry(entry_id: int) -> dict:
    """
    メモリエントリを削除する
    
    Args:
        entry_id (int): 削除するメモリエントリのID
    
    Returns:
        dict: 削除操作の結果
    """
    return _delete_memory_entry_impl(entry_id)

@mcp.tool()
def list_all_memories(limit: int = 50) -> dict:
    """
    すべてのメモリエントリをメタデータと共に一覧表示する
    
    Args:
        limit (int): 返す結果の最大数（デフォルト: 50）
    
    Returns:
        dict: メモリエントリのリストとメタデータ
    """
    return _list_all_memories_impl(limit)

@mcp.tool()
def get_project_rules() -> dict:
    """
    プロジェクトルールタグ付きメモリを取得する
    
    Returns:
        dict: プロジェクトルールのメモリエントリリスト
    """
    return _get_project_rules_impl()

# Pydantic models for request/response validation
from pydantic import BaseModel, Field, field_validator
from typing import Union

class MemoryEntryRequest(BaseModel):
    """Request model for creating/updating memory entries"""
    content: str = Field(..., min_length=1, description="メモリエントリの内容")
    tags: Optional[List[str]] = Field(default=[], description="タグのリスト")
    keywords: Optional[List[str]] = Field(default=[], description="キーワードのリスト")
    summary: Optional[str] = Field(default="", description="短い要約")
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()
    
    @field_validator('tags', 'keywords')
    @classmethod
    def validate_string_lists(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError('Must be a list')
        # Filter out empty strings and strip whitespace
        return [item.strip() for item in v if item and isinstance(item, str) and item.strip()]
    
    @field_validator('summary')
    @classmethod
    def validate_summary(cls, v):
        if v is None:
            return ""
        return v.strip()

class MemoryEntryUpdateRequest(BaseModel):
    """Request model for updating memory entries (all fields optional)"""
    content: Optional[str] = Field(None, min_length=1, description="メモリエントリの内容")
    tags: Optional[List[str]] = Field(None, description="タグのリスト")
    keywords: Optional[List[str]] = Field(None, description="キーワードのリスト")
    summary: Optional[str] = Field(None, description="短い要約")
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Content cannot be empty')
        return v.strip() if v else None
    
    @field_validator('tags', 'keywords')
    @classmethod
    def validate_string_lists(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError('Must be a list')
        # Filter out empty strings and strip whitespace
        return [item.strip() for item in v if item and isinstance(item, str) and item.strip()]
    
    @field_validator('summary')
    @classmethod
    def validate_summary(cls, v):
        if v is None:
            return None
        return v.strip()

class MemoryEntryResponse(BaseModel):
    """Response model for memory entries"""
    id: int
    content: str
    tags: List[str]
    keywords: List[str]
    summary: str
    created_at: str
    updated_at: str

class MemoryEntryListResponse(BaseModel):
    """Response model for memory entry lists"""
    entries: List[MemoryEntryResponse]
    total_count: int
    limit: Optional[int] = None

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

# REST API Endpoints

@app.post("/memories", response_model=MemoryEntryResponse, status_code=201)
async def create_memory_entry(entry: MemoryEntryRequest):
    """
    新しいメモリエントリを作成する
    
    Args:
        entry: メモリエントリの作成リクエスト
    
    Returns:
        作成されたメモリエントリ
    """
    try:
        # Create memory entry
        entry_id = memory_service.add_memory(
            content=entry.content,
            tags=entry.tags,
            keywords=entry.keywords,
            summary=entry.summary
        )
        
        # Return the created entry
        created_entry = memory_service.get_memory_by_id(entry_id)
        logger.info(f"REST API: Created memory entry with ID {entry_id}")
        
        return MemoryEntryResponse(**created_entry)
        
    except (ValidationError, DatabaseError):
        # Re-raise custom exceptions to be handled by exception handlers
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_memory_entry: {e}")
        raise MemoryServerError(f"予期しないエラーが発生しました: {e}")



@app.put("/memories/{entry_id}", response_model=MemoryEntryResponse)
async def update_memory_entry_api(entry_id: int, entry: MemoryEntryUpdateRequest):
    """
    指定されたIDのメモリエントリを更新する
    
    Args:
        entry_id: メモリエントリのID
        entry: メモリエントリの更新リクエスト
    
    Returns:
        更新されたメモリエントリ
    """
    try:
        if entry_id <= 0:
            raise ValidationError(
                "Entry ID must be a positive integer",
                "entry_id",
                entry_id
            )
        
        # Update memory entry
        success = memory_service.update_memory(
            entry_id=entry_id,
            content=entry.content,
            tags=entry.tags,
            keywords=entry.keywords,
            summary=entry.summary
        )
        
        if success:
            # Return the updated entry
            updated_entry = memory_service.get_memory_by_id(entry_id)
            logger.info(f"REST API: Updated memory entry with ID {entry_id}")
            
            return MemoryEntryResponse(**updated_entry)
        else:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse.create_error_response(
                    ErrorCodes.INTERNAL_ERROR,
                    f"Failed to update memory entry with ID {entry_id}",
                    {"entry_id": entry_id}
                )
            )
        
    except (NotFoundError, ValidationError, DatabaseError):
        # Re-raise custom exceptions to be handled by exception handlers
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_memory_entry: {e}")
        raise MemoryServerError(f"予期しないエラーが発生しました: {e}")

@app.delete("/memories/{entry_id}", response_model=SuccessResponse)
async def delete_memory_entry_api(entry_id: int):
    """
    指定されたIDのメモリエントリを削除する
    
    Args:
        entry_id: メモリエントリのID
    
    Returns:
        削除操作の結果
    """
    try:
        if entry_id <= 0:
            raise ValidationError(
                "Entry ID must be a positive integer",
                "entry_id",
                entry_id
            )
        
        # Delete memory entry
        success = memory_service.delete_memory(entry_id)
        
        if success:
            logger.info(f"REST API: Deleted memory entry with ID {entry_id}")
            return SuccessResponse(
                message=f"メモリエントリが正常に削除されました (ID: {entry_id})",
                data={"deleted_entry_id": entry_id}
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse.create_error_response(
                    ErrorCodes.INTERNAL_ERROR,
                    f"Failed to delete memory entry with ID {entry_id}",
                    {"entry_id": entry_id}
                )
            )
        
    except (NotFoundError, ValidationError, DatabaseError):
        # Re-raise custom exceptions to be handled by exception handlers
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_memory_entry: {e}")
        raise MemoryServerError(f"予期しないエラーが発生しました: {e}")

# Search and filtering endpoints (order matters for routing)
# More specific routes must come before generic ones

@app.get("/memories/search", response_model=MemoryEntryListResponse)
async def search_memories_endpoint(
    q: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 10
):
    """
    メモリエントリを検索する（専用検索エンドポイント）
    
    Args:
        q: 検索クエリ（内容、要約、タグ、キーワードから検索）
        tags: 検索対象のタグ（カンマ区切り）
        limit: 返す結果の最大数
    
    Returns:
        検索結果のメモリエントリリスト
    """
    try:
        # Validate limit
        if limit <= 0 or limit > Config.MAX_SEARCH_RESULTS:
            limit = 10
        
        # Parse tags parameter
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Perform search
        results = memory_service.search_memories(
            query=q.strip() if q else None,
            tags=tag_list,
            limit=limit
        )
        
        logger.info(f"REST API: Searched {len(results)} memory entries (q='{q}', tags='{tags}')")
        
        return MemoryEntryListResponse(
            entries=[MemoryEntryResponse(**entry) for entry in results],
            total_count=len(results),
            limit=limit
        )
        
    except DatabaseError as e:
        logger.error(f"Database error in search_memories_endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create_error_response(
                ErrorCodes.DATABASE_ERROR,
                "データベース操作中にエラーが発生しました",
                e.details
            )
        )
    except Exception as e:
        logger.error(f"Unexpected error in search_memories_endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create_error_response(
                ErrorCodes.INTERNAL_ERROR,
                "予期しないエラーが発生しました",
                {"error_type": type(e).__name__}
            )
        )

@app.get("/memories/tags/{tag}", response_model=MemoryEntryListResponse)
async def get_memories_by_tag(tag: str, limit: int = 10):
    """
    指定されたタグでメモリエントリをフィルタリングする
    
    Args:
        tag: フィルタリング対象のタグ
        limit: 返す結果の最大数
    
    Returns:
        指定されたタグを持つメモリエントリのリスト
    """
    try:
        # Validate inputs
        if not tag or not tag.strip():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.create_error_response(
                    ErrorCodes.VALIDATION_ERROR,
                    "Tag cannot be empty",
                    {"field": "tag", "invalid_value": tag}
                )
            )
        
        if limit <= 0 or limit > Config.MAX_SEARCH_RESULTS:
            limit = 10
        
        # Search by tag
        results = memory_service.search_memories(
            query=None,
            tags=[tag.strip()],
            limit=limit
        )
        
        logger.info(f"REST API: Found {len(results)} memory entries with tag '{tag}'")
        
        return MemoryEntryListResponse(
            entries=[MemoryEntryResponse(**entry) for entry in results],
            total_count=len(results),
            limit=limit
        )
        
    except DatabaseError as e:
        logger.error(f"Database error in get_memories_by_tag: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create_error_response(
                ErrorCodes.DATABASE_ERROR,
                "データベース操作中にエラーが発生しました",
                e.details
            )
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_memories_by_tag: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create_error_response(
                ErrorCodes.INTERNAL_ERROR,
                "予期しないエラーが発生しました",
                {"error_type": type(e).__name__}
            )
        )

@app.get("/memories", response_model=MemoryEntryListResponse)
async def list_memories(
    q: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 10
):
    """
    メモリエントリを検索・一覧表示する
    
    Args:
        q: 検索クエリ（内容、要約、タグ、キーワードから検索）
        tags: 検索対象のタグ（カンマ区切り）
        limit: 返す結果の最大数
    
    Returns:
        メモリエントリのリスト
    """
    try:
        # Validate limit
        if limit <= 0 or limit > Config.MAX_SEARCH_RESULTS:
            limit = 10
        
        # Parse tags parameter
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Perform search
        if q or tag_list:
            # Search with query and/or tags
            results = memory_service.search_memories(
                query=q.strip() if q else None,
                tags=tag_list,
                limit=limit
            )
        else:
            # List all memories if no search criteria
            results = memory_service.list_all_memories(limit=limit)
        
        logger.info(f"REST API: Listed/searched {len(results)} memory entries (q='{q}', tags='{tags}')")
        
        return MemoryEntryListResponse(
            entries=[MemoryEntryResponse(**entry) for entry in results],
            total_count=len(results),
            limit=limit
        )
        
    except DatabaseError as e:
        logger.error(f"Database error in list_memories: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create_error_response(
                ErrorCodes.DATABASE_ERROR,
                "データベース操作中にエラーが発生しました",
                e.details
            )
        )
    except Exception as e:
        logger.error(f"Unexpected error in list_memories: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create_error_response(
                ErrorCodes.INTERNAL_ERROR,
                "予期しないエラーが発生しました",
                {"error_type": type(e).__name__}
            )
        )

@app.get("/memories/{entry_id}", response_model=MemoryEntryResponse)
async def get_memory_entry(entry_id: int):
    """
    指定されたIDのメモリエントリを取得する
    
    Args:
        entry_id: メモリエントリのID
    
    Returns:
        メモリエントリ
    """
    try:
        if entry_id <= 0:
            raise ValidationError(
                "Entry ID must be a positive integer",
                "entry_id",
                entry_id
            )
        
        entry = memory_service.get_memory_by_id(entry_id)
        logger.info(f"REST API: Retrieved memory entry with ID {entry_id}")
        
        return MemoryEntryResponse(**entry)
        
    except (NotFoundError, ValidationError, DatabaseError):
        # Re-raise custom exceptions to be handled by exception handlers
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_memory_entry: {e}")
        raise MemoryServerError(f"予期しないエラーが発生しました: {e}")

class ServerManager:
    """Server lifecycle management class"""
    
    def __init__(self):
        self.mcp_server = None
        self.fastapi_server = None
        self.shutdown_event = asyncio.Event()
        self.servers_running = False
    
    async def start_servers(self):
        """Start both MCP and FastAPI servers with proper error handling"""
        try:
            logger.info("=== Memory Server MCP Starting ===")
            logger.info("Configuration:")
            logger.info(f"  Host: {Config.HOST}")
            logger.info(f"  Port: {Config.PORT}")
            logger.info(f"  Log Level: {Config.LOG_LEVEL}")
            logger.info(f"  Database: {Config.DATABASE_PATH}")
            logger.info(f"  Log File: {Config.LOG_FILE}")
            logger.info(f"  Max Search Results: {Config.MAX_SEARCH_RESULTS}")
            
            # Initialize and verify database connection
            logger.info("Initializing database connection...")
            initialize_mcp_server()
            
            # Register all MCP tools (they are already decorated with @mcp.tool())
            logger.info("MCP tools registered:")
            logger.info("- add_note_to_memory: メモリにノートを追加")
            logger.info("- search_memory: キーワードまたはタグでメモリを検索")
            logger.info("- update_memory_entry: 既存のメモリエントリを更新")
            logger.info("- delete_memory_entry: メモリエントリを削除")
            logger.info("- list_all_memories: すべてのメモリエントリを一覧表示")
            logger.info("- get_project_rules: プロジェクトルールタグ付きメモリを取得")
            
            # Start MCP server
            logger.info("Starting MCP server...")
            # fastmcpのrun()ではなくrun_async()を直接使用してasyncio問題を回避
            mcp_task = asyncio.create_task(mcp.run_async("stdio"))
            logger.info("✓ MCP server started successfully")
            
            # Start FastAPI server with enhanced configuration
            logger.info("Starting FastAPI server...")
            config = uvicorn.Config(
                app,
                host=Config.HOST,
                port=Config.PORT,
                log_level=Config.LOG_LEVEL.lower(),
                access_log=False,  # Disable access logs to reduce noise
                server_header=False,  # Remove server header for security
                date_header=False  # Remove date header for performance
            )
            
            self.fastapi_server = uvicorn.Server(config)
            fastapi_task = asyncio.create_task(self.fastapi_server.serve())
            
            logger.info(f"✓ FastAPI server started on http://{Config.HOST}:{Config.PORT}")
            logger.info("=== Memory Server MCP is fully operational ===")
            logger.info("Press Ctrl+C to shutdown gracefully")
            
            self.servers_running = True
            
            # Wait for shutdown signal or server completion
            done, pending = await asyncio.wait(
                [mcp_task, fastapi_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if any server failed
            for task in done:
                if task.exception():
                    logger.error(f"Server task failed: {task.exception()}")
                    raise task.exception()
                    
        except Exception as e:
            logger.error(f"Failed to start servers: {e}")
            await self.shutdown_servers()
            raise
    
    async def shutdown_servers(self):
        """Gracefully shutdown both servers"""
        if not self.servers_running:
            return
            
        logger.info("=== Initiating graceful shutdown ===")
        
        try:
            # Shutdown FastAPI server
            if self.fastapi_server:
                logger.info("Shutting down FastAPI server...")
                self.fastapi_server.should_exit = True
                # Give it a moment to shutdown gracefully
                await asyncio.sleep(0.5)
                logger.info("✓ FastAPI server shutdown complete")
            
            # MCP server will be cancelled by the main task cancellation
            logger.info("✓ MCP server shutdown complete")
            
            # Close database connections
            logger.info("Closing database connections...")
            # The connections are managed per-request, so no explicit cleanup needed
            logger.info("✓ Database connections closed")
            
            self.servers_running = False
            logger.info("=== Shutdown complete ===")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def signal_shutdown(self):
        """Signal servers to shutdown"""
        self.shutdown_event.set()

# Global server manager instance
server_manager = ServerManager()

async def main():
    """
    Main function to run both MCP and FastAPI servers concurrently
    Implements proper lifecycle management and graceful shutdown
    """
    import sys
    
    try:
        # Check if we should run only FastAPI for testing
        if len(sys.argv) > 1 and sys.argv[1] == "--api-only":
            logger.info("Starting FastAPI server only (testing mode)...")
            # FastAPI server configuration
            config = uvicorn.Config(
                app=app,
                host=Config.HOST,
                port=Config.PORT,
                log_level=Config.LOG_LEVEL.lower()
            )
            server = uvicorn.Server(config)
            await server.serve()
            return 0
        
        # Setup signal handlers for graceful shutdown
        import signal
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            server_manager.signal_shutdown()
        
        # Register signal handlers (Unix-like systems)
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except AttributeError:
            # Windows doesn't support SIGTERM
            signal.signal(signal.SIGINT, signal_handler)
        
        # Start servers
        await server_manager.start_servers()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.exception("Full error traceback:")
        return 1
    finally:
        # Ensure cleanup
        await server_manager.shutdown_servers()
    
    return 0

def run_server():
    """
    Entry point function that can be called from other modules
    Returns exit code (0 for success, 1 for error)
    """
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

def is_pyinstaller():
    """PyInstallerで実行されているかチェック"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def setup_windows_asyncio():
    """Windowsでのasyncio環境セットアップ"""
    import sys
    import asyncio
    
    if sys.platform.startswith('win'):
        # Windows環境でのイベントループポリシー設定
        if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            logger.info("WindowsProactorEventLoopPolicy を設定しました")
        
        # PyInstaller環境での特別な設定
        if is_pyinstaller():
            # 新しいイベントループを作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("PyInstaller環境用の新しいイベントループを設定しました")
            return loop
    
    return None

if __name__ == "__main__":
    import sys
    import asyncio
    
    if is_pyinstaller():
        # PyInstaller環境での実行
        logger.info("PyInstaller環境で実行中...")
        try:
            # Windows用のasyncio環境をセットアップ
            custom_loop = setup_windows_asyncio()
            
            if custom_loop:
                # カスタムループを使用して実行
                try:
                    exit_code = custom_loop.run_until_complete(main())
                    sys.exit(exit_code)
                finally:
                    custom_loop.close()
            else:
                # 通常の実行方法にフォールバック
                exit_code = asyncio.run(main())
                sys.exit(exit_code)
                
        except Exception as e:
            logger.error(f"PyInstaller execution error: {e}")
            logger.exception("Full error traceback:")
            sys.exit(1)
    else:
        # 通常の実行環境
        # Windows用のasyncio環境をセットアップ（オプション）
        setup_windows_asyncio()
        
        exit_code = run_server()
        sys.exit(exit_code)