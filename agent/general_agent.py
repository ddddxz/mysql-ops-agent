"""
通用智能体

处理通用问题，使用 RAG 知识库。
"""
from langchain_core.messages import HumanMessage, SystemMessage

from model import get_llm
from rag import get_knowledge_base
from utils import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是一个 MySQL 智能运维助手。
你可以回答关于 MySQL 的各种问题，包括配置、优化、故障排查等。

如果有相关知识库内容，请优先参考知识库回答。
{rag_context}"""


async def general_agent(state: dict) -> dict:
    """通用智能体节点（RAG）"""
    llm = get_llm()
    kb = get_knowledge_base()
    
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, "content") else str(last_message)
    
    rag_context = kb.get_context(user_input)
    
    if rag_context:
        system_prompt = SYSTEM_PROMPT.format(rag_context=f"\n相关知识库内容：\n{rag_context}")
    else:
        system_prompt = SYSTEM_PROMPT.format(rag_context="")
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    response = llm.invoke(messages)
    logger.info("通用智能体完成回答")
    
    return {"agent_response": response.content}
