"""
WebSocket 接口路由

提供实时流式对话功能。

功能：
- WebSocket 连接管理
- 流式消息返回
- 心跳保活
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket 接口"])

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


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket) -> None:
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket 连接断开，当前连接数: {len(self.active_connections)}")
    
    async def send_json(self, websocket: WebSocket, data: dict) -> None:
        """发送 JSON 数据"""
        await websocket.send_json(data)
    
    async def broadcast(self, message: str) -> None:
        """广播消息到所有连接"""
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket 对话接口
    
    消息格式：
    - 发送: {"type": "chat", "message": "用户消息", "user_id": "用户ID", "session_id": "会话ID"}
    - 接收: {"type": "chunk", "content": "内容片段"}
    - 接收: {"type": "done", "message": "完整消息", "session_id": "会话ID"}
    - 接收: {"type": "error", "message": "错误信息"}
    - 发送: {"type": "ping"} -> 接收: {"type": "pong"}
    """
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_json(websocket, {
                    "type": "error",
                    "message": "无效的 JSON 格式"
                })
                continue
            
            msg_type = message.get("type")
            
            if msg_type == "ping":
                await manager.send_json(websocket, {"type": "pong"})
                continue
            
            if msg_type == "chat":
                await handle_chat_message(websocket, message)
                continue
            
            await manager.send_json(websocket, {
                "type": "error",
                "message": f"未知的消息类型: {msg_type}"
            })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}", exc_info=True)
        manager.disconnect(websocket)


async def handle_chat_message(websocket: WebSocket, message: dict) -> None:
    """
    处理聊天消息
    
    Args:
        websocket: WebSocket 连接
        message: 消息内容
    """
    user_message = message.get("message", "")
    user_id = message.get("user_id", "default")
    session_id = message.get("session_id")
    
    if not user_message:
        await manager.send_json(websocket, {
            "type": "error",
            "message": "消息内容不能为空"
        })
        return
    
    try:
        agent = await get_agent()
        memory = get_memory()
        
        if session_id and session_id in memory._sessions:
            agent._session_id = session_id
            agent._user_id = user_id
        else:
            agent._session_id = None
            agent._user_id = user_id
        
        await manager.send_json(websocket, {
            "type": "status",
            "message": "正在处理..."
        })
        
        response = await agent.chat(user_message)
        
        chunk_size = 50
        total_chunks = (len(response) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            await manager.send_json(websocket, {
                "type": "chunk",
                "content": chunk,
                "chunk_index": i // chunk_size,
                "total_chunks": total_chunks
            })
        
        await manager.send_json(websocket, {
            "type": "done",
            "message": response,
            "session_id": agent._session_id
        })
        
    except Exception as e:
        logger.error(f"处理消息失败: {e}", exc_info=True)
        await manager.send_json(websocket, {
            "type": "error",
            "message": f"处理失败: {str(e)}"
        })
