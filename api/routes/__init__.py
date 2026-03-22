"""
API 路由模块
"""

from .chat import router as chat_router
from .health import router as health_router
from .ws import router as ws_router

__all__ = ["chat_router", "health_router", "ws_router"]
