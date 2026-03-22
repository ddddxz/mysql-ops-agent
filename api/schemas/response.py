"""
响应模型

定义 API 响应的 Pydantic 模型。
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """
    对话响应模型
    
    Attributes:
        success: 是否成功
        message: Agent 回复内容
        session_id: 会话标识
        intent: 识别的意图
        timestamp: 响应时间戳
    """
    
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="Agent 回复内容")
    session_id: Optional[str] = Field(None, description="会话标识")
    intent: Optional[str] = Field(None, description="识别的意图")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="响应时间戳",
    )


class HealthResponse(BaseModel):
    """
    健康检查响应模型
    
    Attributes:
        status: 服务状态
        version: 服务版本
        mysql_connected: MySQL 连接状态
        mcp_tools_count: MCP 工具数量
        knowledge_base_docs: 知识库文档数量
    """
    
    status: str = Field(..., description="服务状态")
    version: str = Field(default="1.0.0", description="服务版本")
    mysql_connected: bool = Field(..., description="MySQL 连接状态")
    mcp_tools_count: int = Field(default=0, description="MCP 工具数量")
    knowledge_base_docs: int = Field(default=0, description="知识库文档数量")


class ErrorResponse(BaseModel):
    """
    错误响应模型
    
    Attributes:
        code: 错误码
        message: 错误信息
        details: 错误详情
    """
    
    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="错误详情",
    )


class SessionResponse(BaseModel):
    """
    会话响应模型
    
    Attributes:
        session_id: 会话标识
        user_id: 用户标识
        message_count: 消息数量
        created_at: 创建时间
    """
    
    session_id: str = Field(..., description="会话标识")
    user_id: str = Field(..., description="用户标识")
    message_count: int = Field(default=0, description="消息数量")
    created_at: Optional[datetime] = Field(None, description="创建时间")
