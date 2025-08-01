#!/usr/bin/env python3
"""
WebUI専用FastAPIサーバー (ポート8001)
Memory Server MCP のWebインターフェース専用サーバー
"""

import asyncio
import logging
import httpx
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict, Any, List, Optional

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_resource_path(relative_path: str) -> str:
    """PyInstaller対応のリソースパス取得"""
    try:
        # PyInstallerでバンドルされた場合
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # 通常のPython実行の場合
        base_path = Path(__file__).parent
    
    return str(base_path / relative_path)

class WebUIServer:
    """WebUI専用FastAPIサーバー"""
    
    def __init__(self, port: int = 8001, api_port: int = 8002):
        self.port = port
        self.api_port = api_port
        self.api_base_url = f"http://localhost:{api_port}"
        self.app = FastAPI(title="Memory Server WebUI", version="1.0.0")
        
        # PyInstaller対応のテンプレートパス
        templates_path = get_resource_path("templates")
        self.templates = Jinja2Templates(directory=templates_path)
        self.http_client = None
        
        self._setup_routes()
        self._setup_static_files()
    
    def _setup_static_files(self):
        """静的ファイル設定"""
        # PyInstaller対応の静的ファイルパス
        static_path = get_resource_path("static")
        self.app.mount("/static", StaticFiles(directory=static_path), name="static")
    
    def _setup_routes(self):
        """ルート設定"""
        
        @self.app.on_event("startup")
        async def startup():
            """サーバー起動時の初期化"""
            self.http_client = httpx.AsyncClient(timeout=10.0)
            logger.info(f"WebUI Server starting on port {self.port}")
            logger.info(f"API Server connection: {self.api_base_url}")
        
        @self.app.on_event("shutdown")
        async def shutdown():
            """サーバー停止時のクリーンアップ"""
            if self.http_client:
                await self.http_client.aclose()
        
        @self.app.get("/")
        async def index(request: Request):
            """メインページ - メモリ一覧表示"""
            try:
                # MCPサーバーからメモリ一覧を取得
                memories = await self._get_all_memories()
                return self.templates.TemplateResponse(
                    "index.html",
                    {"request": request, "memories": memories}
                )
            except Exception as e:
                logger.error(f"Index page error: {e}")
                return self.templates.TemplateResponse(
                    "error.html",
                    {"request": request, "error": str(e)}
                )
        
        @self.app.get("/create")
        async def create_form(request: Request):
            """新規作成フォーム"""
            return self.templates.TemplateResponse("create.html", {"request": request})
        
        @self.app.get("/edit/{memory_id}")
        async def edit_form(request: Request, memory_id: int):
            """編集フォーム"""
            try:
                # MCPサーバーからメモリ詳細を取得
                memory = await self._get_memory_by_id(memory_id)
                return self.templates.TemplateResponse(
                    "edit.html",
                    {"request": request, "entry": memory}
                )
            except Exception as e:
                logger.error(f"Edit form error: {e}")
                return self.templates.TemplateResponse(
                    "error.html",
                    {"request": request, "error": str(e)}
                )
        
        # API Proxy Endpoints - MCPサーバーへのプロキシ
        
        @self.app.get("/api/memories")
        async def api_get_memories(limit: int = 50):
            """メモリ一覧API"""
            return await self._proxy_request("GET", "/memories", params={"limit": limit})
        
        @self.app.post("/api/memories")
        async def api_create_memory(request: Request):
            """メモリ作成API"""
            body = await request.json()
            return await self._proxy_request("POST", "/memories", json=body)
        
        @self.app.get("/api/memories/search")
        async def api_search_memories(query: Optional[str] = None, tags: Optional[str] = None, limit: int = 10):
            """メモリ検索API"""
            params = {"limit": limit}
            if query:
                params["query"] = query
            if tags:
                params["tags"] = tags
            return await self._proxy_request("GET", "/memories/search", params=params)
        
        @self.app.get("/api/memories/{memory_id}")
        async def api_get_memory(memory_id: int):
            """メモリ取得API"""
            return await self._proxy_request("GET", f"/memories/{memory_id}")
        
        @self.app.put("/api/memories/{memory_id}")
        async def api_update_memory(memory_id: int, request: Request):
            """メモリ更新API"""
            body = await request.json()
            return await self._proxy_request("PUT", f"/memories/{memory_id}", json=body)
        
        @self.app.delete("/api/memories/{memory_id}")
        async def api_delete_memory(memory_id: int):
            """メモリ削除API"""
            return await self._proxy_request("DELETE", f"/memories/{memory_id}")
        
        
        @self.app.get("/health")
        async def health_check():
            """ヘルスチェック"""
            try:
                # APIサーバーのヘルスチェック
                api_health = await self._proxy_request("GET", "/health")
                return {
                    "status": "healthy",
                    "webui_port": self.port,
                    "api_connection": self.api_base_url,
                    "api_health": api_health
                }
            except Exception as e:
                return {
                    "status": "degraded",
                    "webui_port": self.port,
                    "api_connection": self.api_base_url,
                    "error": str(e)
                }
    
    async def _proxy_request(self, method: str, path: str, **kwargs) -> Dict[Any, Any]:
        """MCPサーバーへのプロキシリクエスト"""
        if not self.http_client:
            raise HTTPException(status_code=503, detail="HTTP client not initialized")
        
        url = f"{self.api_base_url}{path}"
        
        try:
            response = await self.http_client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Request error to API server: {e}")
            raise HTTPException(status_code=503, detail=f"API server connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from API server: {e.response.status_code}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error(f"Unexpected error in proxy request: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_all_memories(self) -> List[Dict[Any, Any]]:
        """全メモリ取得（WebUI用）"""
        try:
            result = await self._proxy_request("GET", "/memories", params={"limit": 100})
            return result.get("entries", [])  # API側は"entries"キーを使用
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []
    
    async def _get_memory_by_id(self, memory_id: int) -> Dict[Any, Any]:
        """ID指定メモリ取得"""
        response = await self._proxy_request("GET", f"/memories/{memory_id}")
        # APIサーバーは MemoryEntryResponse 構造 {"success": bool, "message": str, "entry": {...}} で返すため
        # テンプレートで期待している entry オブジェクトを取り出す
        return response.get("entry", {})
    
    async def run(self):
        """サーバー起動"""
        config = uvicorn.Config(
            app=self.app,
            host="localhost",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

def create_webui_server(port: int = 8001, api_port: int = 8002) -> WebUIServer:
    """WebUIサーバー作成関数"""
    return WebUIServer(port=port, api_port=api_port)

async def main():
    """スタンドアロン実行用メイン関数"""
    server = create_webui_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())