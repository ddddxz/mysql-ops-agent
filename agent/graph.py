"""
LangGraph 多智能体工作流

使用 LangGraph 实现多智能体协作：
1. 路由节点：LLM 判断用户意图
2. 专业智能体：监控、诊断、优化
3. 通用智能体：RAG 知识库
4. 规划智能体：多步骤复杂任务

智能体通过 MCP 工具自动调用数据库操作。

新增功能：
- 全局错误处理节点
- 智能体执行失败降级
- 友好的错误提示
- 复杂任务规划执行
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from .router import classify_intent, route_by_intent
from .monitor_agent import monitor_agent
from .diagnosis_agent import diagnosis_agent
from .optimization_agent import optimization_agent
from .general_agent import general_agent
from .planner_agent import planner_agent
from utils import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    """智能体状态"""
    messages: list
    intent: str
    agent_response: str
    error: str | None


def error_handler(state: dict) -> dict:
    """
    错误处理节点
    
    当智能体执行失败时，返回友好的错误提示
    """
    error = state.get("error", "")
    intent = state.get("intent", "general")
    
    error_messages = {
        "monitor": "抱歉，监控功能暂时不可用。可能的原因：\n"
                   "1. MySQL 数据库连接异常\n"
                   "2. 监控工具调用超时\n\n"
                   "请检查数据库连接状态后重试。",
                   
        "diagnosis": "抱歉，诊断功能暂时不可用。可能的原因：\n"
                     "1. MySQL 数据库连接异常\n"
                     "2. 诊断工具调用超时\n\n"
                     "请检查数据库连接状态后重试。",
                     
        "optimization": "抱歉，优化功能暂时不可用。可能的原因：\n"
                        "1. MySQL 数据库连接异常\n"
                        "2. 优化工具调用超时\n\n"
                        "请检查数据库连接状态后重试。",
                        
        "planner": "抱歉，规划功能暂时不可用。可能的原因：\n"
                   "1. MySQL 数据库连接异常\n"
                   "2. 工具调用超时\n\n"
                   "请检查数据库连接状态后重试。",
                        
        "general": "抱歉，处理您的请求时出现错误。请稍后重试。",
    }
    
    response = error_messages.get(intent, error_messages["general"])
    
    logger.error(f"智能体执行失败 (intent={intent}): {error}")
    
    return {
        "agent_response": response,
        "error": None,
    }


async def safe_monitor_agent(state: dict) -> dict:
    """监控智能体（带错误处理）"""
    try:
        return await monitor_agent(state)
    except Exception as e:
        logger.error(f"监控智能体执行失败: {e}")
        return {
            **state,
            "error": str(e),
        }


async def safe_diagnosis_agent(state: dict) -> dict:
    """诊断智能体（带错误处理）"""
    try:
        return await diagnosis_agent(state)
    except Exception as e:
        logger.error(f"诊断智能体执行失败: {e}")
        return {
            **state,
            "error": str(e),
        }


async def safe_optimization_agent(state: dict) -> dict:
    """优化智能体（带错误处理）"""
    try:
        return await optimization_agent(state)
    except Exception as e:
        logger.error(f"优化智能体执行失败: {e}")
        return {
            **state,
            "error": str(e),
        }


async def safe_general_agent(state: dict) -> dict:
    """通用智能体（带错误处理）"""
    try:
        return await general_agent(state)
    except Exception as e:
        logger.error(f"通用智能体执行失败: {e}")
        return {
            **state,
            "error": str(e),
        }


async def safe_planner_agent(state: dict) -> dict:
    """规划智能体（带错误处理）"""
    try:
        return await planner_agent(state)
    except Exception as e:
        logger.error(f"规划智能体执行失败: {e}")
        return {
            **state,
            "error": str(e),
        }


def should_handle_error(state: dict) -> str:
    """判断是否需要错误处理"""
    if state.get("error"):
        return "error_handler"
    return END


def build_graph() -> StateGraph:
    """构建工作流图"""
    graph = StateGraph(AgentState)
    
    graph.add_node("classify", classify_intent)
    graph.add_node("monitor", safe_monitor_agent)
    graph.add_node("diagnosis", safe_diagnosis_agent)
    graph.add_node("optimization", safe_optimization_agent)
    graph.add_node("general", safe_general_agent)
    graph.add_node("planner", safe_planner_agent)
    graph.add_node("error_handler", error_handler)
    
    graph.set_entry_point("classify")
    
    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "monitor": "monitor",
            "diagnosis": "diagnosis",
            "optimization": "optimization",
            "general": "general",
            "planner": "planner",
        }
    )
    
    graph.add_conditional_edges("monitor", should_handle_error, {
        "error_handler": "error_handler",
        END: END,
    })
    graph.add_conditional_edges("diagnosis", should_handle_error, {
        "error_handler": "error_handler",
        END: END,
    })
    graph.add_conditional_edges("optimization", should_handle_error, {
        "error_handler": "error_handler",
        END: END,
    })
    graph.add_conditional_edges("general", should_handle_error, {
        "error_handler": "error_handler",
        END: END,
    })
    graph.add_conditional_edges("planner", should_handle_error, {
        "error_handler": "error_handler",
        END: END,
    })
    
    graph.add_edge("error_handler", END)
    
    logger.info("工作流图构建完成")
    return graph.compile()


_graph = None


def get_graph():
    """获取工作流图（单例）"""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
