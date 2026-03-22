"""
MCP 工具加载器

通过 langchain-mcp-adapters 加载 MCP 工具。
使用 MultiServerMCPClient 自动管理会话。

功能：
- 工具调用重试机制（使用 with_retry 装饰器）
- 超时控制
- 错误日志记录
"""

import asyncio
import sys
from functools import wraps
from typing import Callable, Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from utils import get_logger

logger = get_logger(__name__)

_client: MultiServerMCPClient | None = None
_tools_cache: list | None = None

MAX_RETRIES = 3
RETRY_DELAY = 1.0
TOOL_TIMEOUT = 30.0


def with_retry(
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY,
    timeout: float = TOOL_TIMEOUT,
):
    """
    异步函数重试装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        timeout: 单次调用超时时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                    if attempt > 0:
                        logger.info(f"函数 {func.__name__} 重试成功 (第 {attempt + 1} 次)")
                    return result
                    
                except asyncio.TimeoutError:
                    last_error = TimeoutError(
                        f"函数调用超时 ({timeout}秒)"
                    )
                    logger.warning(
                        f"函数调用超时 (尝试 {attempt + 1}/{max_retries}): "
                        f"{func.__name__}"
                    )
                    
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"函数调用失败 (尝试 {attempt + 1}/{max_retries}): "
                        f"{func.__name__} - {e}"
                    )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
            
            logger.error(
                f"函数调用最终失败: {func.__name__} - {last_error}"
            )
            raise last_error
            
        return wrapper
    return decorator


async def _load_tools() -> list:
    """内部函数：加载 MCP 工具"""
    global _client
    _client = MultiServerMCPClient(
        {
            "mysql_ops": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "agent.mcp_server"],
            }
        }
    )
    return await _client.get_tools()


@with_retry(max_retries=3, retry_delay=2.0, timeout=60.0)
async def init_mcp_session() -> None:
    """初始化 MCP 会话并加载工具（带重试）"""
    global _client, _tools_cache
    
    if _client is not None:
        return
    
    _tools_cache = await _load_tools()
    logger.info(f"加载 MCP 工具: {len(_tools_cache)} 个")


async def close_mcp_session() -> None:
    """关闭 MCP 会话"""
    global _client, _tools_cache
    _client = None
    _tools_cache = None
    logger.info("MCP 会话已关闭")


def get_mcp_tools() -> list:
    """获取 MCP 工具（已缓存的）"""
    global _tools_cache
    if _tools_cache is None:
        raise RuntimeError("工具未加载，请先调用 await init_mcp_session()")
    return _tools_cache


def get_tools_by_names(tool_names: list[str]) -> list:
    """根据名称获取工具子集"""
    tools = get_mcp_tools()
    return [t for t in tools if t.name in tool_names]


def get_tool_by_name(tool_name: str) -> Any | None:
    """根据名称获取单个工具"""
    tools = get_mcp_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None
