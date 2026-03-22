"""
用户认证模块

提供 JWT token 认证功能。

功能：
- 用户登录验证（从数据库读取）
- JWT token 生成和验证
- 用户权限管理
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import User, UserRole, get_session
from utils import get_logger

logger = get_logger(__name__)

SECRET_KEY = "mysql_intelligent_ops_secret_key_2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


class Token(BaseModel):
    """Token 响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    """用户信息响应模型"""
    username: str
    role: str
    permissions: list[str]


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


def hash_password(password: str) -> str:
    """密码哈希"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(plain_password) == hashed_password


def create_access_token(username: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT access token
    
    简化实现，使用时间戳和签名
    """
    import hashlib
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    expire_timestamp = int(expire.timestamp())
    
    data = f"{username}|{expire_timestamp}"
    signature = hashlib.sha256(f"{data}{SECRET_KEY}".encode()).hexdigest()[:32]
    
    token = f"{data}|{signature}"
    return token


def decode_token(token: str) -> Optional[dict]:
    """
    解码并验证 token
    
    Returns:
        解码成功返回用户信息，失败返回 None
    """
    import hashlib
    
    try:
        parts = token.split("|")
        if len(parts) != 3:
            return None
        
        username, expire_str, signature = parts
        expire_timestamp = int(expire_str)
        
        data = f"{username}|{expire_timestamp}"
        expected_signature = hashlib.sha256(f"{data}{SECRET_KEY}".encode()).hexdigest()[:32]
        
        if signature != expected_signature:
            return None
        
        if datetime.now().timestamp() > expire_timestamp:
            return None
        
        return {"username": username}
        
    except Exception as e:
        logger.error(f"Token 解码失败: {e}")
        return None


def get_user_from_db(username: str, session: Session) -> Optional[User]:
    """从数据库获取用户"""
    return session.query(User).filter(User.username == username, User.is_active == True).first()


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> dict:
    """
    获取当前用户（依赖注入）
    
    用于需要认证的接口
    """
    token = credentials.credentials
    token_data = decode_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_from_db(token_data["username"], session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "username": user.username,
        "role": user.role.value,
        "permissions": user.permissions
    }


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    session: Session = Depends(get_session)
) -> Optional[dict]:
    """
    获取当前用户（可选）
    
    用于可选认证的接口
    """
    if not credentials:
        return None
    
    token_data = decode_token(credentials.credentials)
    if not token_data:
        return None
    
    user = get_user_from_db(token_data["username"], session)
    if not user:
        return None
    
    return {
        "username": user.username,
        "role": user.role.value,
        "permissions": user.permissions
    }


def check_permission(user: dict, required_permission: str) -> bool:
    """
    检查用户权限
    
    Args:
        user: 用户信息
        required_permission: 需要的权限
        
    Returns:
        是否有权限
    """
    permissions = user.get("permissions", [])
    
    if "all" in permissions:
        return True
    
    return required_permission in permissions
