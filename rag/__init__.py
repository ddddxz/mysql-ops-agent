"""
RAG 模块

提供检索增强生成功能，包括知识库管理和对话记忆。
"""

from .knowledge_base import KnowledgeBase, get_knowledge_base
from .memory import MemoryManager, get_memory_manager

__all__ = [
    "KnowledgeBase",
    "get_knowledge_base",
    "MemoryManager",
    "get_memory_manager",
]
