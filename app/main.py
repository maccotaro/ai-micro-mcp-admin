"""FastAPI Application"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import mcp
from app.services.mcp_server import get_mcp_server

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル"""
    # Startup
    logger.info(f"{settings.app_name} starting up...")

    # MCPサーバー初期化
    mcp_server = get_mcp_server()
    logger.info("MCP Server initialized")

    yield

    # Shutdown
    logger.info(f"{settings.app_name} shutting down...")


# FastAPIアプリケーション
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(mcp.router)


@app.get("/health")
async def health_check():
    """ヘルスチェック（認証不要）"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/")
async def root():
    """ルート（認証不要）"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "mcp_endpoint": "/mcp",
        "authentication": "JWT Bearer token required"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """グローバル例外ハンドラー"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )
