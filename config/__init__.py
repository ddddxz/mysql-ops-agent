"""
配置模块

管理所有配置项，支持从环境变量和 .env 文件加载。
"""

from .settings import settings

__all__ = ["settings"]
