"""
路由节点

负责判断用户意图，决定由哪个智能体处理。

新增功能：
- LLM 调用超时控制
- 意图分类失败降级处理
- 关键词匹配作为备用方案
"""

import asyncio
from langchain_core.messages import HumanMessage, AIMessage

from model import get_llm
from utils import get_logger

logger = get_logger(__name__)

INTENT_TIMEOUT = 10.0

MONITOR_KEYWORDS = [
    "监控", "状态", "健康", "检查", "连接数", "qps", "qps", "缓冲池",
    "buffer pool", "线程", "processlist", "show status", "show variables",
    "指标", "性能指标", "运行状态", "当前状态",
]

DIAGNOSIS_KEYWORDS = [
    "诊断", "慢查询", "slow query", "锁", "lock", "死锁", "deadlock",
    "故障", "排查", "问题", "超时", "timeout", "连接失败", "报错",
    "错误", "error", "性能下降", "卡顿", "hang", "分析问题",
]

OPTIMIZATION_KEYWORDS = [
    "优化", "sql优化", "索引", "index", "调优", "配置优化", "参数优化",
    "性能优化", "查询优化", "建议", "改进", "提升性能",
]

PLANNER_KEYWORDS = [
    "全面", "完整", "综合", "详细", "报告", "分析报告", "巡检",
    "全面检查", "完整诊断", "综合分析", "多步骤", "一系列",
    "先检查", "然后", "最后", "同时", "并且",
]


def classify_intent_by_keywords(user_input: str) -> str:
    """
    基于关键词的意图分类（降级方案）
    
    Args:
        user_input: 用户输入
        
    Returns:
        意图类别
    """
    user_input_lower = user_input.lower()
    
    planner_score = sum(
        1 for kw in PLANNER_KEYWORDS 
        if kw.lower() in user_input_lower
    )
    
    if planner_score >= 2:
        logger.info(f"关键词分类降级: planner (分数: {planner_score})")
        return "planner"
    
    monitor_score = sum(
        1 for kw in MONITOR_KEYWORDS 
        if kw.lower() in user_input_lower
    )
    diagnosis_score = sum(
        1 for kw in DIAGNOSIS_KEYWORDS 
        if kw.lower() in user_input_lower
    )
    optimization_score = sum(
        1 for kw in OPTIMIZATION_KEYWORDS 
        if kw.lower() in user_input_lower
    )
    
    scores = {
        "monitor": monitor_score,
        "diagnosis": diagnosis_score,
        "optimization": optimization_score,
    }
    
    max_score = max(scores.values())
    
    if max_score > 0:
        intent = max(scores, key=scores.get)
        logger.info(f"关键词分类降级: {intent} (分数: {scores})")
        return intent
    
    return "general"


def classify_intent(state: dict) -> dict:
    """
    路由节点：判断用户意图
    
    包含错误处理和降级逻辑：
    1. LLM 调用超时 → 使用关键词匹配
    2. LLM 返回无效结果 → 使用关键词匹配
    3. LLM 调用失败 → 使用关键词匹配
    """
    llm = get_llm()
    
    messages = state["messages"]
    
    if not messages:
        logger.warning("消息列表为空，使用默认意图")
        return {"intent": "general"}
    
    last_message = messages[-1]
    user_input = last_message.content if hasattr(last_message, "content") else str(last_message)
    
    history_text = ""
    if len(messages) > 1:
        history_parts = []
        for m in messages[:-1]:
            if hasattr(m, "content") and m.content:
                role = "用户" if isinstance(m, HumanMessage) else "助手"
                content = m.content[:300] if len(m.content) > 300 else m.content
                history_parts.append(f"{role}: {content}")
        history_text = "\n".join(history_parts)
    
    prompt = f"""你是一个意图分类器，需要根据对话历史判断用户当前问题的意图。

## 对话历史:
{history_text if history_text else "(无历史对话)"}

## 当前用户输入:
{user_input}

## 意图类别:
- monitor: 监控类问题（连接数、QPS、缓冲池、状态指标、健康检查）
- diagnosis: 诊断类问题（慢查询、锁、故障排查、性能下降、连接问题、超时分析）
- optimization: 优化类问题（SQL优化、索引建议、配置调优、参数优化）
- planner: 复杂任务（需要多个步骤、全面检查、综合分析、巡检报告）
- general: 通用问题（闲聊、问候、其他问题）

## 判断规则:
1. 如果用户请求"全面检查"、"完整诊断"、"综合分析"等需要多个步骤的任务，选择 planner
2. 如果用户输入是简短确认词（如"需要"、"是的"、"好的"、"请帮我"、"可以"），必须根据对话历史中助手最后提出的问题来判断意图
3. 如果用户在追问"刚才"、"之前"、"上面"的结果，根据历史对话判断意图
4. 如果用户问的是 MySQL 运维相关问题，选择对应类别
5. 如果无法确定，选择 general

## 示例:
用户: 帮我做一个全面的健康检查
意图: planner（需要多个步骤）

用户: 先检查连接数，然后分析慢查询，最后给出优化建议
意图: planner（多步骤任务）

历史: 助手: 需要我帮你生成优化 wait_timeout 的 SQL 吗？
用户: 需要
意图: optimization（因为助手问的是优化问题）

只返回一个类别名称（monitor/diagnosis/optimization/planner/general），不要其他内容。"""

    try:
        response = asyncio.run(
            asyncio.wait_for(
                asyncio.to_thread(llm.invoke, [HumanMessage(content=prompt)]),
                timeout=INTENT_TIMEOUT
            )
        )
        intent = response.content.strip().lower()
        
        if intent not in ["monitor", "diagnosis", "optimization", "planner", "general"]:
            logger.warning(f"LLM 返回无效意图: {intent}，使用关键词降级")
            intent = classify_intent_by_keywords(user_input)
        
        logger.info(f"意图识别: {intent}")
        return {"intent": intent}
        
    except asyncio.TimeoutError:
        logger.warning(f"意图分类超时 ({INTENT_TIMEOUT}秒)，使用关键词降级")
        intent = classify_intent_by_keywords(user_input)
        return {"intent": intent}
        
    except Exception as e:
        logger.error(f"意图分类失败: {e}，使用关键词降级")
        intent = classify_intent_by_keywords(user_input)
        return {"intent": intent}


def route_by_intent(state: dict) -> str:
    """根据意图路由"""
    return state.get("intent", "general")
