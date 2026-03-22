"""
知识库管理

使用 LangChain + Chroma 实现知识检索。
支持持久化存储和增量更新（基于 MD5 去重）。
"""

import hashlib
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from config import settings
from model import get_embeddings
from utils import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "mysql_knowledge"


class KnowledgeBase:
    """
    知识库管理器
    
    负责加载文档、构建向量索引、检索相关内容。
    """
    
    def __init__(self, knowledge_dir: str | None = None, persist_directory: str | None = None) -> None:
        self._knowledge_dir = Path(knowledge_dir or settings.knowledge_dir)
        self._persist_directory = Path(persist_directory or settings.chroma_persist_dir)
        self._md5_file = self._persist_directory / "md5.txt"
        
        self._embeddings = get_embeddings()
        
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )
        
        self._vectorstore: Chroma | None = None
        self._initialized = False
    
    def initialize(self) -> None:
        """初始化知识库"""
        if self._initialized:
            return
        
        self._load_vectorstore()
        self._load_documents()
        self._initialized = True
    
    def _compute_md5(self, file_path: Path) -> str:
        """计算文件的 MD5 哈希（分段处理，避免内存溢出）"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def _load_md5_set(self) -> set[str]:
        """加载已存储的 MD5 集合"""
        if not self._md5_file.exists():
            return set()
        
        with open(self._md5_file, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    
    def _save_md5(self, md5: str) -> None:
        """保存 MD5 到文件"""
        self._persist_directory.mkdir(parents=True, exist_ok=True)
        with open(self._md5_file, "a", encoding="utf-8") as f:
            f.write(md5 + "\n")
    
    def _load_vectorstore(self) -> None:
        """加载已有向量库"""
        if self._persist_directory.exists():
            try:
                self._vectorstore = Chroma(
                    collection_name=COLLECTION_NAME,
                    persist_directory=str(self._persist_directory),
                    embedding_function=self._embeddings,
                )
                count = self._vectorstore._collection.count()
                logger.info(f"加载已有向量库: {count} 个文档片段")
            except Exception as e:
                logger.warning(f"加载向量库失败: {e}")
                self._vectorstore = None
    
    def _load_documents(self) -> None:
        """加载文档到向量库（自动去重）"""
        if not self._knowledge_dir.exists():
            logger.warning(f"知识目录不存在: {self._knowledge_dir}")
            return
        
        existing_md5s = self._load_md5_set()
        new_documents = []
        
        for file_path in self._knowledge_dir.iterdir():
            if file_path.suffix not in [".txt", ".md"]:
                continue
            
            try:
                md5 = self._compute_md5(file_path)
                
                if md5 in existing_md5s:
                    logger.info(f"文档已存在，跳过: {file_path.name}")
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                document = Document(
                    page_content=content,
                    metadata={"source": str(file_path)},
                )
                new_documents.append((document, md5))
                logger.info(f"发现新文档: {file_path.name}")
                
            except Exception as e:
                logger.warning(f"加载文件失败 {file_path}: {e}")
        
        if new_documents:
            texts = self._text_splitter.split_documents([doc for doc, _ in new_documents])
            
            if self._vectorstore:
                self._vectorstore.add_documents(texts)
            else:
                self._persist_directory.mkdir(parents=True, exist_ok=True)
                self._vectorstore = Chroma.from_documents(
                    documents=texts,
                    embedding=self._embeddings,
                    collection_name=COLLECTION_NAME,
                    persist_directory=str(self._persist_directory),
                )
            
            for _, md5 in new_documents:
                self._save_md5(md5)
            
            logger.info(f"添加 {len(new_documents)} 个新文档, {len(texts)} 个片段")
        else:
            if not self._vectorstore:
                logger.warning("没有文档可加载")
    
    def search(self, query: str, k: int | None = None) -> list[dict[str, Any]]:
        """搜索相关文档"""
        if not self._vectorstore:
            return []
        
        top_k = k or settings.rag_top_k
        results = self._vectorstore.similarity_search_with_score(query, k=top_k)
        
        return [
            {
                "content": doc.page_content,
                "score": round(1 - score / 2, 4),
                "source": doc.metadata.get("source", ""),
            }
            for doc, score in results
        ]
    
    def get_context(self, query: str, max_length: int = 2000) -> str:
        """获取查询相关的上下文"""
        results = self.search(query)
        context_parts = []
        total_length = 0
        
        for result in results:
            content = result["content"]
            if total_length + len(content) > max_length:
                break
            context_parts.append(content)
            total_length += len(content)
        
        return "\n\n".join(context_parts)


_knowledge_base: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库实例（单例）"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
        _knowledge_base.initialize()
    return _knowledge_base
