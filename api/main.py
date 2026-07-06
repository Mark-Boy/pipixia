"""
pipixia API - 跨境电商自动上架工具后端
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("pipixia API 启动中...")
    # 初始化数据库表
    await init_db()
    logger.info("数据库初始化完成")
    # TODO: 加载敏感词库
    # TODO: 注册定时任务
    logger.info("pipixia API 启动完成")
    yield
    logger.info("pipixia API 关闭中...")
    # TODO: 清理资源


app = FastAPI(
    title="pipixia API",
    description="跨境电商自动上架工具 API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 健康检查 ====================
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """系统健康检查"""
    return {
        "status": "ok",
        "service": "pipixia-api",
        "version": "0.1.0",
    }


# ==================== 路由注册 ====================
from .routers import auth, shops, products, audit, listings, settings, webhooks, reports, media, translate
from .database import init_db

# API v1 路由（需要认证）
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(shops.router, prefix="/api/v1", tags=["Shops"])
app.include_router(products.router, prefix="/api/v1", tags=["Products"])
app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
app.include_router(listings.router, prefix="/api/v1", tags=["Listings"])
app.include_router(settings.router, prefix="/api/v1", tags=["Settings"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
app.include_router(media.router, prefix="/api/v1", tags=["Media"])
app.include_router(translate.router, prefix="/api/v1", tags=["Translate"])

# Webhook 路由（公开）
app.include_router(webhooks.router, prefix="/webhook", tags=["Webhooks"])
