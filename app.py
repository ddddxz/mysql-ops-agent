"""
MySQL 智能运维 Agent

主入口文件，使用 LangGraph 实现多智能体协作。

技术栈：
- LangChain: LLM 封装
- MCP: 工具协议（通用）
- LangGraph: 多智能体工作流
- RAG: 知识检索增强
- 长对话记忆: 多轮对话支持
"""

import asyncio
import sys

from utils import get_database, get_logger
from rag import get_knowledge_base, get_memory_manager
from agent import init_mcp_session, close_mcp_session, get_graph

logger = get_logger(__name__)


class MySQLAgent:
    """
    MySQL 智能运维 Agent
    
    使用 LangGraph 实现真正的多智能体协作：
    - LLM 自动判断意图
    - 智能体自动调用 MCP 工具
    - 条件路由实现智能分发
    - 多轮对话记忆支持
    """
    
    def __init__(self, user_id: str = "default") -> None:
        self._user_id = user_id
        self._db = get_database()
        self._knowledge_base = get_knowledge_base()
        self._memory = get_memory_manager()
        self._graph = None
        
        self._session_id: str | None = None
    
    async def initialize(self) -> bool:
        """初始化 Agent（异步）"""
        if not self._db.connect():
            logger.warning("MySQL 数据库连接失败，将仅提供知识库问答")
        else:
            logger.info("MySQL 数据库连接成功")
        
        await init_mcp_session()
        
        self._graph = get_graph()
        
        logger.info("MySQL Agent 初始化完成")
        return True
    
    async def shutdown(self) -> None:
        """关闭 Agent"""
        await close_mcp_session()
        self._db.close()
        logger.info("MySQL Agent 已关闭")
    
    def clear_history(self) -> None:
        """清除对话历史"""
        if self._session_id:
            self._memory.clear_session(self._session_id)
            self._session_id = None
            logger.info("对话历史已清除")
    
    async def chat(self, message: str) -> str:
        """
        与 Agent 对话（支持多轮对话记忆）
        
        Args:
            message: 用户消息
            
        Returns:
            Agent 回复
        """
        if not self._session_id:
            self._session_id = self._memory.create_session(self._user_id)
        
        self._memory.add_user_message(self._session_id, message)
        
        history_messages = self._memory.get_messages(self._session_id)
        
        state = {
            "messages": history_messages,
            "intent": "",
            "agent_response": "",
        }
        
        result = await self._graph.ainvoke(state)
        
        response = result.get("agent_response", "抱歉，我无法处理这个问题。")
        
        self._memory.add_ai_message(self._session_id, response)
        
        return response


async def run_interactive() -> None:
    """运行交互式对话"""
    print("=" * 50)
    print("  MySQL 智能运维 Agent (LangGraph 版)")
    print("  输入 'quit' 或 'exit' 退出")
    print("  输入 'clear' 清除对话历史")
    print("=" * 50)
    
    agent = MySQLAgent()
    await agent.initialize()
    
    try:
        while True:
            try:
                print("\n你: ", end="", flush=True)
                user_input = sys.stdin.readline().strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n再见!")
                    break
                
                if user_input.lower() == "clear":
                    agent.clear_history()
                    print("\n对话历史已清除!")
                    continue
                
                response = await agent.chat(user_input)
                print(f"\nAgent: {response}")
                
            except KeyboardInterrupt:
                print("\n\n再见!")
                break
    finally:
        await agent.shutdown()


def main() -> None:
    """主入口"""
    asyncio.run(run_interactive())


if __name__ == "__main__":
    main()
