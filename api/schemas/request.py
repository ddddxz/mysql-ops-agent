"""
请求模型

定义 API 请求的 Pydantic 模型。
"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    对话请求模型
    
    Attributes:
        message: 用户消息内容
        user_id: 用户标识（可选，默认为 default）
        session_id: 会话标识（可选，用于多轮对话）
        clear_history: 是否清除对话历史
    """
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="用户消息内容",
        examples=["检查一下 MySQL 健康状态"],
    )
    user_id: Optional[str] = Field(
        default="default",
        max_length=64,
        description="用户标识",
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="会话标识（用于多轮对话）",
    )
    clear_history: bool = Field(
        default=False,
        description="是否清除对话历史",
    )
