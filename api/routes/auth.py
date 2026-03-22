"""
认证接口路由

提供用户登录和认证相关的 API 接口。

功能：
- 用户登录
- 获取当前用户信息
- Token 验证
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta
from sqlalchemy.orm import Session

from api.auth import (
    Token,
    UserResponse,
    LoginRequest,
    verify_password,
    create_access_token,
    get_current_user,
    get_user_from_db,
    ACCESS_TOKEN_EXPIRE_HOURS,
)
from db import get_session
from utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["认证接口"])


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    description="使用用户名和密码登录，返回 JWT token",
)
async def login(
    request: LoginRequest,
    session: Session = Depends(get_session)
) -> Token:
    """
    用户登录
    
    Args:
        request: 登录请求（用户名和密码）
        
    Returns:
        Token: 包含 access_token 的响应
    """
    user = get_user_from_db(request.username, session)
    
    if not user:
        logger.warning(f"登录失败: 用户不存在 - {request.username}")
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"登录失败: 密码错误 - {request.username}")
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    access_token = create_access_token(
        username=user.username,
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    
    logger.info(f"用户登录成功: {user.username} (角色: {user.role.value})")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user={
            "username": user.username,
            "role": user.role.value,
            "permissions": user.permissions
        }
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="获取当前登录用户的信息",
)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    """
    获取当前用户信息
    
    Args:
        current_user: 当前用户（通过依赖注入获取）
        
    Returns:
        UserResponse: 用户信息
    """
    return UserResponse(
        username=current_user["username"],
        role=current_user["role"],
        permissions=current_user["permissions"]
    )


@router.post(
    "/verify",
    summary="验证 Token",
    description="验证当前 token 是否有效",
)
async def verify_token(current_user: dict = Depends(get_current_user)) -> dict:
    """
    验证 token 是否有效
    
    Args:
        current_user: 当前用户（通过依赖注入获取）
        
    Returns:
        验证结果
    """
    return {
        "valid": True,
        "user": {
            "username": current_user["username"],
            "role": current_user["role"]
        }
    }


@router.post(
    "/logout",
    summary="用户登出",
    description="用户登出（前端清除 token 即可）",
)
async def logout() -> dict:
    """
    用户登出
    
    由于使用 JWT token，服务端不需要维护会话状态，
    前端清除 token 即可完成登出。
    
    Returns:
        登出结果
    """
    return {
        "success": True,
        "message": "登出成功"
    }
