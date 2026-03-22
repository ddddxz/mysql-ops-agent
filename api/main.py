"""
FastAPI 主入口

提供 MySQL 智能运维 Web API 服务。

运行方式:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat_router, health_router, ws_router
from api.routes.scheduler import router as scheduler_router
from api.routes.auth import router as auth_router
from api.routes.stream import router as stream_router
from utils import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    
    启动时延迟初始化资源，关闭时清理资源。
    """
    logger.info("MySQL 智能运维 API 服务启动中...")
    
    from db import setup_database
    setup_database()
    logger.info("数据库初始化完成")
    
    from scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("定时任务调度器已启动")
    
    yield
    
    scheduler.stop()
    logger.info("定时任务调度器已停止")
    
    try:
        from agent import close_mcp_session
        await close_mcp_session()
    except Exception:
        pass
    logger.info("MySQL 智能运维 API 服务已关闭")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        FastAPI: 应用实例
    """
    app = FastAPI(
        title="MySQL 智能运维 API",
        description="""
## MySQL 智能运维 Agent API

基于 LangGraph + MCP 协议的 MySQL 智能运维助手，支持：

- **多智能体协作**：监控、诊断、优化、通用四大智能体
- **多轮对话**：支持上下文记忆
- **RAG 知识库**：MySQL 运维知识检索增强
- **MCP 工具**：18 个专业运维工具

### 主要接口

| 接口 | 说明 |
|------|------|
| POST /api/chat | 对话接口 |
| GET /api/health | 健康检查 |
| POST /api/chat/session | 创建会话 |
| DELETE /api/chat/session/{id} | 清除会话 |
| POST /api/scheduler/job/health-check | 创建定时健康检查 |
| POST /api/scheduler/job/report | 创建定时报表 |
| POST /api/scheduler/health-check/run | 立即健康检查 |
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(health_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(ws_router)
    app.include_router(scheduler_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(stream_router, prefix="/api")
    
    @app.get("/", tags=["根路径"])
    async def root() -> dict[str, str]:
        """根路径，返回 API 信息"""
        return {
            "name": "MySQL 智能运维 API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/health",
        }
    
    return app


app = create_app()


def main() -> None:
    """启动服务（命令行入口）"""
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
