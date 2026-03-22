"""
配置设置

使用 pydantic-settings 管理配置，支持环境变量和 .env 文件。
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM配置
    llm_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model_name: str = "qwen-plus"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    llm_embedding_model: str = "text-embedding-v3"

    # MySQL 数据库配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = ""  # 不指定默认数据库，可跨库查询

    # RAG 配置
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 4

    # 路径配置
    knowledge_dir: str = "knowledge/docs"
    chroma_persist_dir: str = "chroma_db"
    log_dir: str = "logs"

    @property
    def api_key(self) -> str:
        """获取 API Key"""
        return os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
