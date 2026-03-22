"""
LLM 模型封装

使用 LangChain 的 ChatOpenAI 封装大语言模型。
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def get_llm() -> ChatOpenAI:
    """
    获取 LLM 实例（单例）
    
    Returns:
        ChatOpenAI 实例
    """
    llm = ChatOpenAI(
        model=settings.llm_model_name,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.api_key,
        base_url=settings.llm_api_base,
    )
    logger.info(f"LLM 模型初始化: {settings.llm_model_name}")
    return llm
