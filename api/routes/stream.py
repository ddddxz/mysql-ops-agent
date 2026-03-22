"""
流式对话接口路由

提供 SSE 流式对话功能。

功能：
- 流式消息返回
- 深度思考模式（显示推理过程）
- 简洁模式（仅显示结果）
"""

import json
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio

from api.schemas import ChatRequest
from utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/stream", tags=["流式对话接口"])

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


async def stream_chat(
    message: str,
    user_id: str = "default",
    session_id: Optional[str] = None,
    deep_think: bool = False,
) -> None:
    """
    流式对话生成器
    
    Args:
        message: 用户消息
        user_id: 用户 ID
        session_id: 会话 ID
        deep_think: 是否启用深度思考模式
    """
    from model import get_llm
    from agent import get_graph
    from rag import get_knowledge_base
    from db import get_session_factory, User
    from sqlalchemy.orm import Session
    
    agent = await get_agent()
    memory = get_memory()
    kb = get_knowledge_base()
    
    factory = get_session_factory()
    db_session = factory()
    try:
        db_user = db_session.query(User).filter(User.username == user_id).first()
        db_user_id = db_user.id if db_user else 1
    finally:
        db_session.close()
    
    if session_id and memory.session_exists(session_id):
        agent._session_id = session_id
        agent._user_id = db_user_id
    else:
        agent._session_id = None
        agent._user_id = db_user_id
    
    if not agent._session_id:
        agent._session_id = memory.create_session(db_user_id)
    
    memory.add_user_message(agent._session_id, message)
    history_messages = memory.get_messages(agent._session_id)
    
    yield f"data: {json.dumps({'type': 'session', 'session_id': agent._session_id}, ensure_ascii=False)}\n\n"
    
    if deep_think:
        yield f"data: {json.dumps({'type': 'think_start', 'message': '正在分析您的问题...'}, ensure_ascii=False)}\n\n"
        
        rag_context = kb.get_context(message)
        if rag_context:
            yield f"data: {json.dumps({'type': 'thinking', 'content': '📚 检索知识库相关内容...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)
        
        yield f"data: {json.dumps({'type': 'thinking', 'content': '🔍 分析用户意图...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)
        
        yield f"data: {json.dumps({'type': 'thinking', 'content': '🤖 调用智能体处理...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)
    
    try:
        from agent import init_mcp_session
        await init_mcp_session()
        
        graph = get_graph()
        state = {
            "messages": history_messages,
            "intent": "",
            "agent_response": "",
        }
        
        if deep_think:
            result = await graph.ainvoke(state)
            
            intent = result.get("intent", "unknown")
            yield f"data: {json.dumps({'type': 'thinking', 'content': f'📋 识别意图: {intent}'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)
            
            response = result.get("agent_response", "抱歉，我无法处理这个问题。")
            
            yield f"data: {json.dumps({'type': 'think_end'}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'response_start'}, ensure_ascii=False)}\n\n"
            
            chunk_size = 20
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)
            
            yield f"data: {json.dumps({'type': 'done', 'session_id': agent._session_id}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'response_start'}, ensure_ascii=False)}\n\n"
            
            result = await graph.ainvoke(state)
            response = result.get("agent_response", "抱歉，我无法处理这个问题。")
            
            chunk_size = 20
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)
            
            yield f"data: {json.dumps({'type': 'done', 'session_id': agent._session_id}, ensure_ascii=False)}\n\n"
        
        memory.add_ai_message(agent._session_id, response)
        
    except Exception as e:
        logger.error(f"流式对话失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': f'处理失败: {str(e)}'}, ensure_ascii=False)}\n\n"


@router.get(
    "/chat",
    summary="流式对话",
    description="SSE 流式返回对话内容，支持深度思考模式",
)
async def stream_chat_endpoint(
    message: str = Query(..., description="用户消息"),
    user_id: str = Query("default", description="用户 ID"),
    session_id: Optional[str] = Query(None, description="会话 ID"),
    deep_think: bool = Query(False, description="深度思考模式"),
):
    """
    流式对话接口
    
    SSE 事件类型：
    - session: 会话信息
    - think_start: 开始思考
    - thinking: 思考过程
    - think_end: 思考结束
    - response_start: 开始回复
    - chunk: 内容片段
    - done: 完成
    - error: 错误
    """
    return StreamingResponse(
        stream_chat(message, user_id, session_id, deep_think),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
