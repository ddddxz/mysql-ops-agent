"""
数据库会话管理

提供 SQLAlchemy 会话管理和数据库初始化功能。
"""

import hashlib
import os
from functools import lru_cache
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config import settings
from db.models import Base, User, UserRole
from utils import get_logger

logger = get_logger(__name__)

APP_DATABASE = "mysql_ops"

DEFAULT_ROOT_PASSWORD = os.getenv("DEFAULT_ROOT_PASSWORD", "changeme")


def get_engine(database: Optional[str] = None):
    """
    获取数据库引擎
    
    Args:
        database: 数据库名，为 None 时不指定数据库（用于创建数据库）
    
    Returns:
        SQLAlchemy Engine
    """
    if database:
        dsn = f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}:{settings.mysql_port}/{database}"
    else:
        dsn = f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}:{settings.mysql_port}"
    
    return create_engine(
        dsn,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


@lru_cache
def get_app_engine():
    """获取应用数据库引擎（单例）"""
    return get_engine(APP_DATABASE)


@lru_cache
def get_session_factory():
    """获取会话工厂（单例）"""
    engine = get_app_engine()
    return sessionmaker(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """获取数据库会话（依赖注入）"""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    engine = get_engine()
    
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{APP_DATABASE}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()
    
    logger.info(f"数据库 '{APP_DATABASE}' 已就绪")


def init_database():
    """初始化数据库表"""
    create_database_if_not_exists()
    
    engine = get_engine(APP_DATABASE)
    Base.metadata.create_all(engine)
    logger.info("数据库表创建完成")


def init_default_users():
    """初始化默认用户"""
    factory = get_session_factory()
    session = factory()
    
    try:
        existing = session.query(User).first()
        if existing:
            logger.info("用户数据已存在，跳过初始化")
            return
        
        default_users = [
            User(
                username="root",
                password_hash=hashlib.sha256(DEFAULT_ROOT_PASSWORD.encode()).hexdigest(),
                role=UserRole.ADMIN,
                is_active=True,
            ),
            User(
                username="admin",
                password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
                role=UserRole.ADMIN,
                is_active=True,
            ),
            User(
                username="operator",
                password_hash=hashlib.sha256("oper123".encode()).hexdigest(),
                role=UserRole.OPERATOR,
                is_active=True,
            ),
            User(
                username="viewer",
                password_hash=hashlib.sha256("view123".encode()).hexdigest(),
                role=UserRole.VIEWER,
                is_active=True,
            ),
        ]
        
        session.add_all(default_users)
        session.commit()
        logger.info(f"默认用户初始化完成: root (密码: {DEFAULT_ROOT_PASSWORD}), admin, operator, viewer")
        
    except Exception as e:
        session.rollback()
        logger.error(f"初始化用户失败: {e}")
        raise
    finally:
        session.close()


def setup_database():
    """完整的数据库初始化流程"""
    logger.info("开始初始化数据库...")
    init_database()
    init_default_users()
    logger.info("数据库初始化完成")
