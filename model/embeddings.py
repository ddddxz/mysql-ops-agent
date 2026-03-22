"""
Embedding 模型封装

使用 LangChain 的 DashScopeEmbeddings 封装向量嵌入模型。
"""

from functools import lru_cache

from langchain_community.embeddings import DashScopeEmbeddings

from config import settings
from utils import get_logger

logger = get_logger(__name__)


@lru_cache
def get_embeddings() -> DashScopeEmbeddings:
    """
    获取 Embedding 实例（单例）
    
    Returns:
        DashScopeEmbeddings 实例
    """
    embeddings = DashScopeEmbeddings(
        model=settings.llm_embedding_model,
        dashscope_api_key=settings.api_key,
    )
    logger.info(f"Embedding 模型初始化: {settings.llm_embedding_model}")
    return embeddings
