"""
对话接口路由

提供与 MySQL Agent 对话的 API 接口。

功能：
- 对话接口
- 会话管理（创建、查看、恢复、删除）
- 历史消息查看
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from api.schemas import ChatRequest, ChatResponse, ErrorResponse, SessionResponse
from utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["对话接口"])

_agent_instance = None
_memory_instance = None


async def get_agent():
    """获取 Agent 实例（延迟初始化）"""
    global _agent_instance
    if _agent_instance is None:
        from app import MySQLAgent
        _agent_instance = MySQLAgent()
        await _agent_instance.initialize()
        logger.info("Agent 实例初始化完成")
    return _agent_instance


def get_memory():
    """获取记忆管理器实例"""
    global _memory_instance
    if _memory_instance is None:
        from rag import get_memory_manager
        _memory_instance = get_memory_manager()
    return _memory_instance


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
    summary="发送对话消息",
    description="向 MySQL Agent 发送消息并获取回复，支持多轮对话",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """对话接口"""
    try:
        agent = await get_agent()
        memory = get_memory()
        
        if request.clear_history:
            agent.clear_history()
            logger.info(f"用户 {request.user_id} 清除对话历史")
        
        if request.session_id and memory.session_exists(request.session_id):
            agent._session_id = request.session_id
            agent._user_id = request.user_id
        else:
            agent._session_id = None
            agent._user_id = request.user_id
        
        response = await agent.chat(request.message)
        
        return ChatResponse(
            success=True,
            message=response,
            session_id=agent._session_id,
            intent=None,
        )
        
    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "对话处理失败",
                "details": str(e),
            }
        )


@router.post(
    "/session",
    response_model=SessionResponse,
    summary="创建新会话",
    description="创建一个新的对话会话",
)
async def create_session(user_id: int = 1) -> SessionResponse:
    """创建新会话"""
    memory = get_memory()
    session_id = memory.create_session(user_id)
    
    logger.info(f"创建新会话: {session_id[:8]}... (用户: {user_id})")
    
    return SessionResponse(
        session_id=session_id,
        user_id=user_id,
        message_count=0,
    )


@router.get(
    "/sessions",
    summary="获取会话列表",
    description="获取用户的所有会话或所有会话",
)
async def get_sessions(
    user_id: Optional[int] = Query(None, description="用户 ID，不传则返回所有会话"),
    limit: int = Query(20, ge=1, le=100, description="最大返回数量"),
) -> list[dict]:
    """
    获取会话列表
    
    Args:
        user_id: 用户 ID（可选）
        limit: 最大返回数量
        
    Returns:
        会话信息列表
    """
    memory = get_memory()
    
    if user_id:
        sessions = memory.get_user_sessions(user_id, limit)
    else:
        sessions = memory.get_all_sessions(limit)
    
    return [s.to_dict() for s in sessions]


@router.get(
    "/session/{session_id}",
    response_model=SessionResponse,
    summary="获取会话信息",
    description="获取指定会话的信息",
)
async def get_session_info(session_id: str) -> SessionResponse:
    """获取会话信息"""
    memory = get_memory()
    info = memory.get_session_info(session_id)
    
    if info is None:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "会话不存在", "details": f"Session {session_id} not found"}
        )
    
    return SessionResponse(
        session_id=info.session_id,
        user_id=info.user_id,
        message_count=info.message_count,
        created_at=info.created_at,
    )


@router.get(
    "/session/{session_id}/history",
    summary="获取会话历史",
    description="获取指定会话的对话历史",
)
async def get_session_history(session_id: str) -> dict:
    """
    获取会话历史
    
    Args:
        session_id: 会话标识
        
    Returns:
        会话历史消息列表
    """
    memory = get_memory()
    
    if not memory.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "会话不存在", "details": f"Session {session_id} not found"}
        )
    
    messages = memory.get_messages_as_text(session_id)
    info = memory.get_session_info(session_id)
    
    return {
        "session_id": session_id,
        "user_id": info.user_id if info else "unknown",
        "message_count": len(messages),
        "messages": messages,
    }


@router.post(
    "/session/{session_id}/resume",
    response_model=ChatResponse,
    summary="恢复会话并发送消息",
    description="恢复指定会话并发送新消息",
)
async def resume_session(
    session_id: str,
    message: str,
    user_id: str = "default",
) -> ChatResponse:
    """
    恢复会话并发送消息
    
    Args:
        session_id: 会话标识
        message: 新消息
        user_id: 用户标识
        
    Returns:
        Agent 回复
    """
    memory = get_memory()
    
    if not memory.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "会话不存在", "details": f"Session {session_id} not found"}
        )
    
    agent = await get_agent()
    agent._session_id = session_id
    agent._user_id = user_id
    
    response = await agent.chat(message)
    
    logger.info(f"恢复会话: {session_id[:8]}... (用户: {user_id})")
    
    return ChatResponse(
        success=True,
        message=response,
        session_id=session_id,
        intent=None,
    )


@router.delete(
    "/session/{session_id}",
    summary="清除会话历史",
    description="清除指定会话的对话历史",
)
async def clear_session(session_id: str) -> dict[str, str]:
    """清除会话历史"""
    memory = get_memory()
    
    if not memory.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "会话不存在", "details": f"Session {session_id} not found"}
        )
    
    memory.clear_session(session_id)
    logger.info(f"清除会话历史: {session_id[:8]}...")
    
    return {"status": "success", "message": "会话历史已清除"}
