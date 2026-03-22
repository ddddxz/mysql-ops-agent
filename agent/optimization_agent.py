"""
优化智能体

负责 SQL 优化和配置调优。
使用 LangChain 的 create_react_agent，LLM 自动决定调用哪个工具。
"""
from langgraph.prebuilt import create_react_agent

from model import get_llm
from .tools import get_tools_by_names
from rag import get_knowledge_base
from utils import get_logger

logger = get_logger(__name__)
OPTIMIZATION_TOOLS = [
    "explain_query",
    "analyze_config",
    "get_table_sizes",
    "get_variables",
    "execute_query",
    "configure_slow_query_log",
    "analyze_slow_queries",
    "analyze_indexes",
    "get_index_statistics",
]
SYSTEM_PROMPT = """你是 MySQL 优化专家。
你可以使用以下工具来提供优化建议：
- explain_query: 分析 SQL 执行计划
- analyze_config: 分析配置参数
- get_table_sizes: 查看表大小
- get_variables: 获取系统变量
- configure_slow_query_log: 配置慢查询日志（启用/禁用、设置阈值）
- analyze_slow_queries: 分析慢查询，找出问题 SQL
- analyze_indexes: 分析索引使用情况，找出未使用/冗余索引
- get_index_statistics: 获取表的索引统计信息

根据用户问题，自动选择合适的工具进行分析。
{rag_context}"""

async def optimization_agent(state:dict)->dict:
    """
    优化智能体节点
    LLM 会自动：
    1. 分析用户问题
    2. 决定调用哪个工具
    3. 执行工具并返回结果
    """
    llm=get_llm()
    tools=get_tools_by_names(OPTIMIZATION_TOOLS)
    kb=get_knowledge_base()
    last_message=state["messages"][-1]
    user_input=last_message.content if hasattr(last_message,"content") else str(last_message)
    rag_context=kb.get_context(user_input)
    if rag_context:
        system_prompt = SYSTEM_PROMPT.format(rag_context=f"\n相关知识库内容：\n{rag_context}")
    else:
        system_prompt = SYSTEM_PROMPT.format(rag_context="")
    agent=create_react_agent(llm,tools,prompt=system_prompt)
    result=await agent.ainvoke({"messages":state["messages"]})
    response=result["messages"][-1].content
    logger.info("优化智能体完成回答")
    return {"agent_response":response}