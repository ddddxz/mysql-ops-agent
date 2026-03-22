"""
监控智能体

负责收集和分析 MySQL 状态指标。
使用 LangChain 的 create_react_agent，LLM 自动决定调用哪个工具。
"""
from langgraph.prebuilt import create_react_agent

from model import get_llm
from .tools import get_tools_by_names
from rag import get_knowledge_base
from utils import get_logger

logger=get_logger(__name__)

MONITOR_TOOLS = [
    "collect_metrics",
    "health_check",
    "get_status",
    "get_variables",
    "get_process_list",
    "execute_query",
]

SYSTEM_PROMPT = """你是 MySQL 监控专家。
你可以使用以下工具来收集和分析 MySQL 状态：
- collect_metrics: 收集服务器指标
- health_check: 健康检查
- get_status: 获取状态变量
- get_variables: 获取系统变量
- get_process_list: 获取连接列表

根据用户问题，自动选择合适的工具进行分析。
{rag_context}"""

async def monitor_agent(state:dict)->dict:
    """
    监控智能体节点
    
    LLM 会自动：
    1. 分析用户问题
    2. 决定调用哪个工具
    3. 执行工具并返回结果
    """
    llm=get_llm()
    tools=get_tools_by_names(MONITOR_TOOLS)
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
    logger.info("监控智能体完成回答")
    return {"agent_response":response}


