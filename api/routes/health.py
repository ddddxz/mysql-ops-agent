"""
健康检查路由

提供服务状态检查接口。
"""

from fastapi import APIRouter

from api.schemas import HealthResponse
from utils import get_database, get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查服务运行状态、MySQL 连接状态、MCP 工具加载状态等",
)
async def health_check() -> HealthResponse:
    """
    健康检查接口
    
    Returns:
        HealthResponse: 服务健康状态信息
    """
    db = get_database()
    mysql_connected = db.connect()
    
    mcp_tools_count = 0
    try:
        from agent import get_mcp_tools
        tools = get_mcp_tools()
        mcp_tools_count = len(tools)
    except Exception as e:
        logger.warning(f"获取 MCP 工具数量失败: {e}")
    
    knowledge_base_docs = 0
    try:
        from rag import get_knowledge_base
        kb = get_knowledge_base()
        kb.initialize()
        if kb._vectorstore:
            knowledge_base_docs = kb._vectorstore._collection.count()
    except Exception as e:
        logger.warning(f"获取知识库文档数量失败: {e}")
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        mysql_connected=mysql_connected,
        mcp_tools_count=mcp_tools_count,
        knowledge_base_docs=knowledge_base_docs,
    )


@router.get(
    "/ready",
    summary="就绪检查",
    description="检查服务是否已准备好接收请求",
)
async def readiness_check() -> dict[str, str]:
    """
    就绪检查接口（Kubernetes 就绪探针）
    
    Returns:
        dict: 就绪状态
    """
    return {"status": "ready"}


@router.get(
    "/live",
    summary="存活检查",
    description="检查服务是否存活",
)
async def liveness_check() -> dict[str, str]:
    """
    存活检查接口（Kubernetes 存活探针）
    
    Returns:
        dict: 存活状态
    """
    return {"status": "alive"}
