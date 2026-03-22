"""
诊断智能体

负责故障排查和问题诊断。
使用 LangChain 的 create_react_agent，LLM 自动决定调用哪个工具。
"""

from langgraph.prebuilt import create_react_agent

from model import get_llm
from .tools import get_tools_by_names
from rag import get_knowledge_base
from utils import get_logger

logger = get_logger(__name__)

DIAGNOSIS_TOOLS = [
    "health_check",
    "get_process_list",
    "get_status",
    "get_table_sizes",
    "execute_query",
    "kill_connection",
    "configure_slow_query_log",
    "analyze_slow_queries",
    "analyze_locks",
    "analyze_transactions",
]

SYSTEM_PROMPT = """你是 MySQL 故障诊断专家。
你可以使用以下工具来诊断问题：
- health_check: 健康检查
- get_process_list: 查看当前连接
- get_status: 获取状态变量
- get_table_sizes: 查看表大小
- configure_slow_query_log: 配置慢查询日志（启用/禁用、设置阈值）
- analyze_slow_queries: 分析慢查询
- analyze_locks: 分析锁等待和死锁
- analyze_transactions: 分析事务状态

根据用户问题，自动选择合适的工具进行诊断。

{rag_context}"""


async def diagnosis_agent(state: dict) -> dict:
    """
    诊断智能体节点
    
    LLM 会自动：
    1. 分析用户问题
    2. 决定调用哪个工具
    3. 执行工具并返回结果
    """
    llm = get_llm()
    tools = get_tools_by_names(DIAGNOSIS_TOOLS)
    kb = get_knowledge_base()
    
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, "content") else str(last_message)
    
    rag_context = kb.get_context(user_input)
    
    if rag_context:
        system_prompt = SYSTEM_PROMPT.format(rag_context=f"\n相关知识库内容：\n{rag_context}")
    else:
        system_prompt = SYSTEM_PROMPT.format(rag_context="")
    
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    
    result = await agent.ainvoke({"messages": state["messages"]})
    
    response = result["messages"][-1].content
    logger.info("诊断智能体完成分析")
    
    return {"agent_response": response}
