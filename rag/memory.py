"""
对话记忆管理

使用 MySQL 数据库实现多轮对话记忆。

功能：
- 多用户多会话管理
- 会话历史查看
- 会话恢复
- 会话列表获取
- 数据库持久化存储
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from sqlalchemy.orm import Session

from db import ChatSession, ChatMessage, get_session_factory
from utils import get_logger

logger = get_logger(__name__)


class SessionInfo:
    """会话信息"""
    def __init__(
        self,
        session_id: str,
        user_id: int,
        title: str,
        created_at: datetime,
        updated_at: datetime,
        message_count: int,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.message_count = message_count
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.message_count,
        }


class MemoryManager:
    """
    对话记忆管理器
    
    使用 MySQL 数据库管理多用户多会话的对话记忆。
    """
    
    def __init__(self, max_history: int = 20) -> None:
        self.max_history = max_history
        self._session_cache: dict[str, ChatMessageHistory] = {}
    
    def create_session(self, user_id: int, title: str = "新对话") -> str:
        """
        创建新会话
        
        Args:
            user_id: 用户 ID
            title: 会话标题
            
        Returns:
            会话 ID (UUID)
        """
        session_id = str(uuid.uuid4())
        
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                title=title,
            )
            session.add(chat_session)
            session.commit()
            
            logger.debug(f"创建新会话: {session_id} (用户: {user_id})")
            return session_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"创建会话失败: {e}")
            raise
        finally:
            session.close()
    
    def get_or_create_session(self, user_id: int, session_id: Optional[str] = None) -> str:
        """
        获取或创建会话
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID（可选）
            
        Returns:
            会话 ID
        """
        if session_id and self.session_exists(session_id):
            return session_id
        
        return self.create_session(user_id)
    
    def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在
        
        Args:
            session_id: 会话 ID
            
        Returns:
            是否存在
        """
        factory = get_session_factory()
        session = factory()
        
        try:
            count = session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).count()
            return count > 0
        finally:
            session.close()
    
    def add_user_message(self, session_id: str, content: str) -> None:
        """
        添加用户消息
        
        Args:
            session_id: 会话 ID
            content: 消息内容
        """
        self._add_message(session_id, "user", content)
        
        if session_id in self._session_cache:
            self._session_cache[session_id].add_user_message(content)
    
    def add_ai_message(self, session_id: str, content: str, thinking: Optional[str] = None) -> None:
        """
        添加 AI 消息
        
        Args:
            session_id: 会话 ID
            content: 消息内容
            thinking: 思考过程
        """
        self._add_message(session_id, "assistant", content, thinking)
        
        if session_id in self._session_cache:
            self._session_cache[session_id].add_ai_message(content)
    
    def _add_message(self, session_id: str, role: str, content: str, thinking: Optional[str] = None) -> None:
        """添加消息到数据库"""
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_session = session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not chat_session:
                logger.warning(f"会话不存在: {session_id}")
                return
            
            message = ChatMessage(
                session_id=chat_session.id,
                role=role,
                content=content,
                thinking=thinking,
            )
            session.add(message)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"添加消息失败: {e}")
        finally:
            session.close()
    
    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """
        获取会话消息列表
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息列表
        """
        if session_id in self._session_cache:
            return self._session_cache[session_id].messages
        
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_session = session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not chat_session:
                return []
            
            messages = session.query(ChatMessage).filter(
                ChatMessage.session_id == chat_session.id
            ).order_by(ChatMessage.created_at).limit(self.max_history).all()
            
            history = ChatMessageHistory()
            for msg in messages:
                if msg.role == "user":
                    history.add_user_message(msg.content)
                else:
                    history.add_ai_message(msg.content)
            
            self._session_cache[session_id] = history
            return history.messages
            
        finally:
            session.close()
    
    def get_messages_as_text(self, session_id: str) -> list[dict]:
        """
        获取会话消息列表（文本格式）
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息列表，每条消息包含 role 和 content
        """
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_session = session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not chat_session:
                return []
            
            messages = session.query(ChatMessage).filter(
                ChatMessage.session_id == chat_session.id
            ).order_by(ChatMessage.created_at).all()
            
            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "thinking": msg.thinking,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in messages
            ]
            
        finally:
            session.close()
    
    def get_history(self, session_id: str) -> Optional[ChatMessageHistory]:
        """
        获取会话历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话历史对象
        """
        messages = self.get_messages(session_id)
        if messages:
            return ChatMessageHistory(messages=messages)
        return None
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        获取会话信息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话信息对象
        """
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_session = session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not chat_session:
                return None
            
            message_count = session.query(ChatMessage).filter(
                ChatMessage.session_id == chat_session.id
            ).count()
            
            return SessionInfo(
                session_id=chat_session.session_id,
                user_id=chat_session.user_id,
                title=chat_session.title,
                created_at=chat_session.created_at,
                updated_at=chat_session.updated_at,
                message_count=message_count,
            )
            
        finally:
            session.close()
    
    def get_user_sessions(self, user_id: int, limit: int = 50) -> list[SessionInfo]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户 ID
            limit: 最大返回数量
            
        Returns:
            会话信息列表
        """
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_sessions = session.query(ChatSession).filter(
                ChatSession.user_id == user_id
            ).order_by(ChatSession.updated_at.desc()).limit(limit).all()
            
            result = []
            for cs in chat_sessions:
                message_count = session.query(ChatMessage).filter(
                    ChatMessage.session_id == cs.id
                ).count()
                
                result.append(SessionInfo(
                    session_id=cs.session_id,
                    user_id=cs.user_id,
                    title=cs.title,
                    created_at=cs.created_at,
                    updated_at=cs.updated_at,
                    message_count=message_count,
                ))
            
            return result
            
        finally:
            session.close()
    
    def get_all_sessions(self, limit: int = 100) -> list[SessionInfo]:
        """
        获取所有会话
        
        Args:
            limit: 最大返回数量
            
        Returns:
            会话信息列表
        """
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_sessions = session.query(ChatSession).order_by(
                ChatSession.updated_at.desc()
            ).limit(limit).all()
            
            result = []
            for cs in chat_sessions:
                message_count = session.query(ChatMessage).filter(
                    ChatMessage.session_id == cs.id
                ).count()
                
                result.append(SessionInfo(
                    session_id=cs.session_id,
                    user_id=cs.user_id,
                    title=cs.title,
                    created_at=cs.created_at,
                    updated_at=cs.updated_at,
                    message_count=message_count,
                ))
            
            return result
            
        finally:
            session.close()
    
    def clear_session(self, session_id: str) -> None:
        """
        清除会话
        
        Args:
            session_id: 会话 ID
        """
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_session = session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if chat_session:
                session.delete(chat_session)
                session.commit()
            
            if session_id in self._session_cache:
                del self._session_cache[session_id]
            
            logger.debug(f"清除会话: {session_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"清除会话失败: {e}")
        finally:
            session.close()
    
    def update_session_title(self, session_id: str, title: str) -> None:
        """
        更新会话标题
        
        Args:
            session_id: 会话 ID
            title: 新标题
        """
        factory = get_session_factory()
        session = factory()
        
        try:
            chat_session = session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if chat_session:
                chat_session.title = title
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"更新会话标题失败: {e}")
        finally:
            session.close()
    
    def get_session_count(self) -> int:
        """获取当前会话数量"""
        factory = get_session_factory()
        session = factory()
        
        try:
            return session.query(ChatSession).count()
        finally:
            session.close()


_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """获取记忆管理器实例（单例）"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
