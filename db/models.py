"""
数据库模型

使用 SQLAlchemy ORM 定义数据表结构。
数据库：mysql智能运维
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    """SQLAlchemy 基类"""
    pass


class UserRole(enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    """用户表"""
    __tablename__="user"

    id=Column(Integer,primary_key=True,autoincrement=True)
    username=Column(String(50),unique=True,nullable=False,comment="用户名")
    password_hash=Column(String(64),nullable=False,comment="密码哈希")
    role=Column(Enum(UserRole),default=UserRole.VIEWER,comment="角色")
    is_active=Column(Boolean,default=True,comment="是否启用")
    create_at=Column(DateTime,default=datetime.now,comment="创建时间")
    update_at=Column(DateTime,default=datetime.now,onupdate=datetime.now,comment="更新时间")

    sessions=relationship("ChatSession",back_populates="user",cascade="all,delete-orphan")

    @property
    def permissions(self)->list[str]:
        """根据角色返回权限列表"""
        permissions_map={
            UserRole.ADMIN:["all", "read", "write", "delete", "admin"],
            UserRole.OPERATOR:["read", "write"],
            UserRole.VIEWER:["read"]
        }
        return permissions_map.get(self.role,[])

    


class ChatSession(Base):
    """聊天会话表"""
    __tablename__ = "chat_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True, comment="会话UUID")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    title = Column(String(200), default="新对话", comment="会话标题")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """聊天消息表"""
    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_session.id", ondelete="CASCADE"), nullable=False, comment="会话ID")
    role = Column(String(20), nullable=False, comment="角色: user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    thinking = Column(Text, nullable=True, comment="思考过程(JSON)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    session = relationship("ChatSession", back_populates="messages")


class Report(Base):
    """报表记录表"""
    __tablename__ = "report"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(20), nullable=False, comment="报表类型: daily/weekly/monthly")
    title = Column(String(200), nullable=False, comment="报表标题")
    content = Column(Text, nullable=False, comment="报表内容(JSON)")
    file_path = Column(String(500), nullable=True, comment="文件路径")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class HealthCheckLog(Base):
    """健康检查日志表"""
    __tablename__ = "health_check_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False, comment="状态: healthy/warning/error")
    issues = Column(Text, nullable=True, comment="问题列表(JSON)")
    metrics = Column(Text, nullable=True, comment="指标数据(JSON)")
    checked_at = Column(DateTime, default=datetime.now, comment="检查时间")


class AlertRecord(Base):
    """告警记录表"""
    __tablename__ = "alert_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False, comment="告警类型")
    level = Column(String(20), nullable=False, comment="告警级别: info/warning/critical")
    title = Column(String(200), nullable=False, comment="告警标题")
    content = Column(Text, nullable=False, comment="告警内容")
    is_sent = Column(Boolean, default=False, comment="是否已发送")
    sent_at = Column(DateTime, nullable=True, comment="发送时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class JobLog(Base):
    """定时任务执行日志表"""
    __tablename__ = "job_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, index=True, comment="任务ID")
    job_type = Column(String(50), nullable=False, comment="任务类型")
    status = Column(String(20), nullable=False, comment="执行状态: success/failed")
    result = Column(Text, nullable=True, comment="执行结果")
    error_message = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
