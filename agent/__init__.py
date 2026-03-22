"""
Agent 模块

提供多智能体协作系统，使用 LangGraph + MCP。
"""

import os

_is_mcp_server = os.environ.get("MCP_SERVER_MODE") == "1"

if not _is_mcp_server:
    from .graph import get_graph, build_graph, AgentState
    from .tools import init_mcp_session, close_mcp_session, get_mcp_tools, get_tools_by_names
    from .router import classify_intent, route_by_intent
    from .monitor_agent import monitor_agent
    from .diagnosis_agent import diagnosis_agent
    from .optimization_agent import optimization_agent
    from .general_agent import general_agent
    from .planner_agent import planner_agent

    __all__ = [
        "get_graph",
        "build_graph",
        "AgentState",
        "init_mcp_session",
        "close_mcp_session",
        "get_mcp_tools",
        "get_tools_by_names",
        "classify_intent",
        "route_by_intent",
        "monitor_agent",
        "diagnosis_agent",
        "optimization_agent",
        "general_agent",
        "planner_agent",
    ]
