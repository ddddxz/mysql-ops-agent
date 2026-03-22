"""
规划智能体

负责处理复杂的多步骤任务：
1. 分析任务需求
2. 制定执行计划
3. 按步骤执行
4. 汇总结果

适用于需要多个工具协作的复杂场景。
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .tools import get_mcp_tools, init_mcp_session
from model import get_llm
from utils import get_logger

logger = get_logger(__name__)

PLANNER_PROMPT = """你是一个 MySQL 运维规划专家。

你的任务是分析用户的复杂需求，制定执行计划，并按步骤完成。

## 可用工具
{tools_description}

## 工作流程
1. 分析用户需求，判断需要哪些工具
2. 制定执行计划，列出步骤
3. 按顺序执行每个步骤
4. 汇总所有结果，给出综合报告

## 输出格式
请使用以下格式输出：

### 执行计划
1. [步骤1描述]
2. [步骤2描述]
...

### 执行过程
**步骤1: [描述]**
- 工具: [工具名]
- 结果: [结果摘要]

**步骤2: [描述]**
- 工具: [工具名]
- 结果: [结果摘要]

### 综合结论
[汇总所有步骤的结果，给出最终结论和建议]
"""

TASK_DECOMPOSITION_PROMPT = """分析以下任务，判断是否需要分解为多个步骤。

任务: {task}

如果任务需要多个工具协作或多个步骤才能完成，请列出执行计划。
如果任务简单，直接执行即可。

请回答：
1. 是否需要分解: 是/否
2. 如果需要分解，列出步骤（每步说明使用什么工具）
3. 如果不需要，说明使用什么工具直接执行
"""


class PlannerAgent:
    """规划智能体"""
    
    def __init__(self):
        self.llm = get_llm()
        self.tools = None
    
    async def _init_tools(self):
        """初始化工具"""
        if self.tools is None:
            await init_mcp_session()
            self.tools = get_mcp_tools()
        return self.tools
    
    def _get_tools_description(self) -> str:
        """获取工具描述"""
        if not self.tools:
            return "工具未加载"
        
        descriptions = []
        for tool in self.tools:
            desc = f"- {tool.name}: {tool.description[:100]}..."
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    async def analyze_task(self, user_input: str) -> dict:
        """
        分析任务复杂度
        
        Args:
            user_input: 用户输入
            
        Returns:
            任务分析结果
        """
        tools = await self._init_tools()
        
        prompt = TASK_DECOMPOSITION_PROMPT.format(task=user_input)
        
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        
        content = response.content
        
        needs_decomposition = "是否需要分解: 是" in content
        
        return {
            "needs_decomposition": needs_decomposition,
            "analysis": content,
        }
    
    async def execute_with_plan(self, user_input: str) -> str:
        """
        按计划执行复杂任务
        
        Args:
            user_input: 用户输入
            
        Returns:
            执行结果
        """
        tools = await self._init_tools()
        
        tools_description = self._get_tools_description()
        
        prompt = PLANNER_PROMPT.format(tools_description=tools_description)
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"请帮我完成以下任务：\n\n{user_input}")
        ]
        
        llm_with_tools = self.llm.bind_tools(tools)
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            response = await llm_with_tools.ainvoke(messages)
            
            messages.append(response)
            
            if not response.tool_calls:
                return response.content
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                logger.info(f"规划智能体调用工具: {tool_name}({tool_args})")
                
                try:
                    tool = next((t for t in tools if t.name == tool_name), None)
                    if tool:
                        result = await tool.ainvoke(tool_args)
                        messages.append({
                            "role": "tool",
                            "content": str(result),
                            "tool_call_id": tool_call["id"]
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "content": f"工具 {tool_name} 不存在",
                            "tool_call_id": tool_call["id"]
                        })
                except Exception as e:
                    logger.error(f"工具调用失败: {tool_name} - {e}")
                    messages.append({
                        "role": "tool",
                        "content": f"工具调用失败: {str(e)}",
                        "tool_call_id": tool_call["id"]
                    })
        
        return "任务执行超时，请简化任务后重试。"


_planner_agent: PlannerAgent | None = None


def get_planner_agent() -> PlannerAgent:
    """获取规划智能体实例（单例）"""
    global _planner_agent
    if _planner_agent is None:
        _planner_agent = PlannerAgent()
    return _planner_agent


async def planner_agent(state: dict) -> dict:
    """
    规划智能体节点
    
    Args:
        state: 工作流状态
        
    Returns:
        更新后的状态
    """
    messages = state.get("messages", [])
    user_input = messages[-1].content if messages else ""
    
    logger.info(f"规划智能体处理: {user_input[:50]}...")
    
    agent = get_planner_agent()
    response = await agent.execute_with_plan(user_input)
    
    return {
        **state,
        "agent_response": response,
    }
