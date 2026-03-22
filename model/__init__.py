"""
模型模块

封装 LLM 和 Embedding 模型。
"""

from .llm import get_llm
from .embeddings import get_embeddings

__all__ = [
    "get_llm",
    "get_embeddings",
]
