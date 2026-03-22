"""
提示词模块

提供各种 Agent 的提示词模板。
"""

from .system_prompts import SYSTEM_PROMPT, COORDINATOR_PROMPT
from .agent_prompts import MONITOR_PROMPT, DIAGNOSIS_PROMPT, OPTIMIZATION_PROMPT

__all__ = [
    "SYSTEM_PROMPT",
    "COORDINATOR_PROMPT",
    "MONITOR_PROMPT",
    "DIAGNOSIS_PROMPT",
    "OPTIMIZATION_PROMPT",
]
