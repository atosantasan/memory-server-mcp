#!/usr/bin/env python3
"""
API専用FastAPIサーバー (ポート8002)
Memory Server MCP のREST API専用サーバー
main.py から分離して独立運用
"""

import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import json

from fastapi import FastAPI, HTTPException, Request
import uvicorn

# PyInstaller環境用のリソースパス取得関数
def get_resource_path(relative_path):
    """PyInstaller環境でのリソースパス取得"""
    import sys
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller環境
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # 開発環境
        return relative_path

# 独立したコンフィグ設定 (main.pyと統一)
class Config:
    """API Server Configuration"""
    import os
    
    # Default values
    DATABASE_PATH = os.getenv("MEMORY_DB_PATH", "memory.db")
    HOST = os.getenv("MEMORY_SERVER_HOST", "localhost")
    PORT = int(os.getenv("MEMORY_SERVER_PORT", "8000"))
    API_PORT = int(os.getenv("MEMORY_API_PORT", "8002"))  # API専用ポート
    LOG_LEVEL = os.getenv("MEMORY_LOG_LEVEL", "INFO").upper()
    MAX_SEARCH_RESULTS = int(os.getenv("MEMORY_MAX_SEARCH_RESULTS", "100"))
    LOG_FILE = os.getenv("MEMORY_LOG_FILE", "memory_server.log")
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # HTTP transport設定
    MCP_HTTP_PATH = os.getenv("MCP_HTTP_PATH", "/mcp")
    
    # Validate configuration
    @classmethod
    def validate_config(cls):
        """Validate configuration values"""
        if cls.PORT < 1 or cls.PORT > 65535:
            raise ValueError(f"Invalid port number: {cls.PORT}")
        
        if cls.API_PORT < 1 or cls.API_PORT > 65535:
            raise ValueError(f"Invalid API port number: {cls.API_PORT}")
        
        if cls.MAX_SEARCH_RESULTS < 1 or cls.MAX_SEARCH_RESULTS > 1000:
            raise ValueError(f"Invalid max search results: {cls.MAX_SEARCH_RESULTS}")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL not in valid_log_levels:
            raise ValueError(f"Invalid log level: {cls.LOG_LEVEL}. Must be one of {valid_log_levels}")
        
        return True

# 独立したデータクラス定義 (循環インポート回避)
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

@dataclass  
class MemoryEntryRequest:
    content: str
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    summary: Optional[str] = None

@dataclass
class MemoryEntryResponse:
    success: bool
    message: str
    entry: Optional[MemoryEntry] = None

@dataclass
class MemoryEntryListResponse:
    success: bool
    message: str
    entries: List[MemoryEntry]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SuccessResponse:
    success: bool
    message: str

# 独立した例外クラス定義 (main.pyと統一)
class MemoryServerError(Exception):
    """Base exception for memory server errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

class NotFoundError(MemoryServerError):
    """Raised when a resource is not found"""
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

class ErrorResponse:
    @staticmethod
    def log_error(error: Exception, context: str):
        logger = logging.getLogger(__name__)
        logger.error(f"{context}: {error}")

# 独立したMemoryService実装 (循環インポート回避)  
class MemoryService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
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
            logging.getLogger(__name__).info("Database initialized successfully with schema and indexes")
    
    def add_memory(self, content: str, tags: List[str] = None, keywords: List[str] = None, summary: str = None) -> int:
        """メモリエントリ追加"""
        if not content or not content.strip():
            raise ValidationError("Content is required")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO memory_entries (content, tags, keywords, summary) VALUES (?, ?, ?, ?)",
                (content, json.dumps(tags) if tags else None, 
                 json.dumps(keywords) if keywords else None, summary)
            )
            return cursor.lastrowid
    
    def get_memory_by_id(self, entry_id: int) -> MemoryEntry:
        """ID指定でメモリエントリ取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM memory_entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            
            if not row:
                raise NotFoundError(f"Memory entry with ID {entry_id} not found")
            
            return MemoryEntry(
                id=row['id'],
                content=row['content'],
                tags=json.loads(row['tags']) if row['tags'] else [],
                keywords=json.loads(row['keywords']) if row['keywords'] else [],
                summary=row['summary'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    def get_all_memories(self, limit: int = 50) -> List[MemoryEntry]:
        """全メモリエントリ取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM memory_entries ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            
            return [MemoryEntry(
                id=row['id'],
                content=row['content'],
                tags=json.loads(row['tags']) if row['tags'] else [],
                keywords=json.loads(row['keywords']) if row['keywords'] else [],
                summary=row['summary'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ) for row in rows]
    
    def search_memories(self, query: str = None, tags: List[str] = None, limit: int = 10) -> List[MemoryEntry]:
        """メモリ検索"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM memory_entries WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (content LIKE ? OR summary LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if tags:
                for tag in tags:
                    sql += " AND tags LIKE ?"
                    params.append(f"%{tag}%")
            
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            return [MemoryEntry(
                id=row['id'],
                content=row['content'],
                tags=json.loads(row['tags']) if row['tags'] else [],
                keywords=json.loads(row['keywords']) if row['keywords'] else [],
                summary=row['summary'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ) for row in rows]
    
    def update_memory(self, entry_id: int, content: str = None, tags: List[str] = None, 
                     keywords: List[str] = None, summary: str = None) -> MemoryEntry:
        """メモリエントリ更新"""
        if not self.get_memory_by_id(entry_id):  # 存在確認
            raise NotFoundError(f"Memory entry with ID {entry_id} not found")
        
        updates = []
        params = []
        
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        if keywords is not None:
            updates.append("keywords = ?") 
            params.append(json.dumps(keywords))
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        
        if not updates:
            raise ValidationError("No fields to update")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(entry_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE memory_entries SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        
        return self.get_memory_by_id(entry_id)
    
    def delete_memory(self, entry_id: int):
        """メモリエントリ削除"""
        if not self.get_memory_by_id(entry_id):  # 存在確認
            raise NotFoundError(f"Memory entry with ID {entry_id} not found")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
            conn.commit()
    
    def get_memories_by_tag(self, tag: str, limit: int = 50) -> List[MemoryEntry]:
        """タグ指定でメモリエントリ取得"""
        return self.search_memories(tags=[tag], limit=limit)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIServer:
    """REST API専用FastAPIサーバー"""
    
    def __init__(self, port: int = 8002):
        self.port = port
        self.app = FastAPI(title="Memory Server API", version="1.0.0")
        self.memory_service = None
        
        self._setup_routes()
    
    def _setup_routes(self):
        """APIルート設定"""
        
        @self.app.on_event("startup")
        async def startup():
            """サーバー起動時の初期化"""
            try:
                # データベースファイルは実行ファイルと同じフォルダから参照
                def get_database_path(db_filename):
                    """実行ファイルと同じディレクトリからデータベースファイルのパスを取得"""
                    import sys
                    if hasattr(sys, 'frozen') and sys.frozen:
                        # PyInstaller EXE環境 - 実行ファイルのディレクトリを取得
                        exe_dir = os.path.dirname(sys.executable)
                        return os.path.join(exe_dir, db_filename)
                    else:
                        # 開発環境 - カレントディレクトリから参照
                        return db_filename
                
                database_path = get_database_path(Config.DATABASE_PATH)
                self.memory_service = MemoryService(database_path)
                logger.info(f"✅ API Server starting on port {self.port}")
                logger.info(f"📊 Database: {database_path}")
            except Exception as e:
                logger.error(f"❌ API Server startup failed: {e}")
                raise
        
        # Health Check
        @self.app.get("/health")
        async def health_check():
            """ヘルスチェック"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database": "connected",
                "port": self.port
            }
        
        # REST API Endpoints
        
        @self.app.post("/memories", response_model=MemoryEntryResponse, status_code=201)
        async def create_memory_entry(entry: MemoryEntryRequest):
            """新しいメモリエントリを作成する"""
            try:
                entry_id = self.memory_service.add_memory(
                    content=entry.content,
                    tags=entry.tags,
                    keywords=entry.keywords,
                    summary=entry.summary
                )
                
                created_entry = self.memory_service.get_memory_by_id(entry_id)
                return MemoryEntryResponse(
                    success=True,
                    message=f"メモリエントリが作成されました (ID: {entry_id})",
                    entry=created_entry
                )
                
            except ValidationError as e:
                ErrorResponse.log_error(e, "REST API: create_memory_entry")
                raise HTTPException(status_code=400, detail=e.message)
            except DatabaseError as e:
                ErrorResponse.log_error(e, "REST API: create_memory_entry")
                raise HTTPException(status_code=500, detail="データベース操作中にエラーが発生しました")
        
        @self.app.put("/memories/{entry_id}", response_model=MemoryEntryResponse)
        async def update_memory_entry(entry_id: int, entry: MemoryEntryRequest):
            """メモリエントリを更新する"""
            try:
                updated_entry = self.memory_service.update_memory(
                    entry_id=entry_id,
                    content=entry.content,
                    tags=entry.tags,
                    keywords=entry.keywords,
                    summary=entry.summary
                )
                
                return MemoryEntryResponse(
                    success=True,
                    message=f"メモリエントリが更新されました (ID: {entry_id})",
                    entry=updated_entry
                )
                
            except NotFoundError as e:
                ErrorResponse.log_error(e, "REST API: update_memory_entry")
                raise HTTPException(status_code=404, detail=e.message)
            except ValidationError as e:
                ErrorResponse.log_error(e, "REST API: update_memory_entry")
                raise HTTPException(status_code=400, detail=e.message)
            except DatabaseError as e:
                ErrorResponse.log_error(e, "REST API: update_memory_entry")
                raise HTTPException(status_code=500, detail="データベース操作中にエラーが発生しました")
        
        @self.app.delete("/memories/{entry_id}", response_model=SuccessResponse)
        async def delete_memory_entry(entry_id: int):
            """メモリエントリを削除する"""
            try:
                self.memory_service.delete_memory(entry_id)
                return SuccessResponse(
                    success=True,
                    message=f"メモリエントリが削除されました (ID: {entry_id})"
                )
                
            except NotFoundError as e:
                ErrorResponse.log_error(e, "REST API: delete_memory_entry")
                raise HTTPException(status_code=404, detail=e.message)
            except DatabaseError as e:
                ErrorResponse.log_error(e, "REST API: delete_memory_entry")
                raise HTTPException(status_code=500, detail="データベース操作中にエラーが発生しました")
        
        @self.app.get("/memories/search", response_model=MemoryEntryListResponse)
        async def search_memories(
            query: Optional[str] = None,
            tags: Optional[str] = None,
            limit: int = 10
        ):
            """メモリを検索する"""
            try:
                tag_list = []
                if tags:
                    tag_list = [tag.strip() for tag in tags.split(",")]
                
                entries = self.memory_service.search_memories(
                    query=query,
                    tags=tag_list,
                    limit=limit
                )
                
                return MemoryEntryListResponse(
                    success=True,
                    message=f"{len(entries)}件のメモリエントリが見つかりました",
                    entries=entries,
                    metadata={
                        "query": query,
                        "tags": tag_list,
                        "limit": limit
                    }
                )
                
            except ValidationError as e:
                ErrorResponse.log_error(e, "REST API: search_memories")
                raise HTTPException(status_code=400, detail=e.message)
            except DatabaseError as e:
                ErrorResponse.log_error(e, "REST API: search_memories")
                raise HTTPException(status_code=500, detail="データベース操作中にエラーが発生しました")
        
        @self.app.get("/memories/tags/{tag}", response_model=MemoryEntryListResponse)
        async def get_memories_by_tag(tag: str, limit: int = 50):
            """指定されたタグを持つメモリエントリを取得する"""
            try:
                entries = self.memory_service.get_memories_by_tag(tag, limit)
                return MemoryEntryListResponse(
                    success=True,
                    message=f"タグ '{tag}' を持つ {len(entries)} 件のメモリエントリを取得しました",
                    entries=entries,
                    metadata={
                        "tag": tag,
                        "limit": limit
                    }
                )
                
            except ValidationError as e:
                ErrorResponse.log_error(e, "REST API: get_memories_by_tag")
                raise HTTPException(status_code=400, detail=e.message)
            except DatabaseError as e:
                ErrorResponse.log_error(e, "REST API: get_memories_by_tag")
                raise HTTPException(status_code=500, detail="データベース操作中にエラーが発生しました")
        
        @self.app.get("/memories", response_model=MemoryEntryListResponse)
        async def get_all_memories(limit: int = 50):
            """すべてのメモリエントリを取得する"""
            try:
                entries = self.memory_service.get_all_memories(limit)
                return MemoryEntryListResponse(
                    success=True,
                    message=f"{len(entries)}件のメモリエントリを取得しました",
                    entries=entries,
                    metadata={
                        "limit": limit
                    }
                )
                
            except DatabaseError as e:
                ErrorResponse.log_error(e, "REST API: get_all_memories")
                raise HTTPException(status_code=500, detail="データベース操作中にエラーが発生しました")
        
        @self.app.get("/memories/{entry_id}", response_model=MemoryEntryResponse)
        async def get_memory_entry(entry_id: int):
            """指定されたIDのメモリエントリを取得する"""
            try:
                entry = self.memory_service.get_memory_by_id(entry_id)
                return MemoryEntryResponse(
                    success=True,
                    message=f"メモリエントリを取得しました (ID: {entry_id})",
                    entry=entry
                )
                
            except NotFoundError as e:
                ErrorResponse.log_error(e, "REST API: get_memory_entry")
                raise HTTPException(status_code=404, detail=e.message)
            except DatabaseError as e:
                ErrorResponse.log_error(e, "REST API: get_memory_entry")
                raise HTTPException(status_code=500, detail="データベース操作中にエラーが発生しました")
    
    async def run(self):
        """APIサーバーを起動"""
        config = uvicorn.Config(
            app=self.app,
            host="localhost",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

def create_api_server(port: int = 8002) -> APIServer:
    """APIサーバー作成関数"""
    return APIServer(port=port)

# モジュールレベルでappを公開 (インポート用)
_api_server_instance = create_api_server()
app = _api_server_instance.app

async def main():
    """スタンドアロン実行用メイン関数"""
    server = create_api_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())