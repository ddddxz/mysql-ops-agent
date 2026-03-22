# MySQL 智能运维 Agent

## 项目简介

基于 LangGraph + MCP 协议的 MySQL 智能运维助手，支持多智能体协作、多轮对话记忆、RAG 知识库检索。

## 技术栈

- **LLM**: LangChain + 智谱 AI (GLM-4)
- **Agent 框架**: LangGraph (多智能体协作)
- **工具协议**: MCP (Model Context Protocol)
- **向量数据库**: ChromaDB (RAG 知识库)
- **数据库**: MySQL 8.0+

## 项目结构

```
MySQL智能运维/
├── agent/                    # 智能体模块
│   ├── __init__.py          # 模块导出
│   ├── graph.py             # LangGraph 工作流定义
│   ├── router.py            # 意图路由（监控/诊断/优化/通用）
│   ├── monitor_agent.py     # 监控智能体
│   ├── diagnosis_agent.py   # 诊断智能体
│   ├── optimization_agent.py # 优化智能体
│   ├── general_agent.py     # 通用智能体（RAG）
│   ├── mcp_server.py        # MCP 工具服务器（18个工具）
│   └── tools.py             # MCP 工具加载器
│
├── config/                   # 配置模块
│   ├── __init__.py
│   └── settings.py          # 环境变量配置
│
├── model/                    # 模型模块
│   ├── __init__.py
│   ├── llm.py               # LLM 封装
│   └── embeddings.py        # 向量嵌入模型
│
├── rag/                      # RAG 模块
│   ├── __init__.py
│   ├── knowledge_base.py    # 知识库管理
│   └── memory.py            # 对话记忆管理
│
├── knowledge/                # 知识库文档
│   └── docs/                # MySQL 运维知识文档
│       ├── mysql_slow_query_analysis.md
│       ├── mysql_lock_transaction_analysis.md
│       ├── mysql_index_optimization.md
│       └── ...
│
├── utils/                    # 工具模块
│   ├── __init__.py
│   ├── database.py          # MySQL 数据库连接
│   └── logger.py            # 日志工具
│
├── prompts/                  # 提示词模块
│   ├── __init__.py
│   ├── agent_prompts.py     # 智能体提示词
│   └── system_prompts.py    # 系统提示词
│
├── chroma_db/               # ChromaDB 向量数据库
├── logs/                    # 日志目录
├── .env                     # 环境变量配置
├── app.py                   # 主入口
└── Agent.md                 # 本文件
```

## 智能体架构

```
用户输入
    ↓
┌─────────────────────────────────────────┐
│           router.py (意图识别)            │
│  根据对话历史判断意图：monitor/diagnosis/  │
│  optimization/general                    │
└─────────────────────────────────────────┘
    ↓
┌─────────┬─────────┬─────────┬─────────┐
│ monitor │diagnosis│optimiza │ general │
│ _agent  │ _agent  │tion_agen│ _agent  │
│         │         │   t     │         │
└─────────┴─────────┴─────────┴─────────┘
    ↓           ↓           ↓           ↓
┌─────────────────────────────────────────┐
│          MCP Tools (18个工具)            │
│  - 监控类: collect_metrics, health_check │
│  - 诊断类: analyze_locks, analyze_trans  │
│  - 优化类: analyze_indexes, explain_query│
│  - 通用类: execute_query, kill_connection│
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│              MySQL 数据库                │
└─────────────────────────────────────────┘
```

## MCP 工具列表 (18个)

### 监控类
| 工具名 | 功能 |
|--------|------|
| `collect_metrics` | 收集服务器指标（连接数、QPS、缓冲池命中率） |
| `health_check` | 健康检查 |
| `get_status` | 获取状态变量 |
| `get_variables` | 获取系统变量 |
| `get_process_list` | 获取当前连接列表 |

### 诊断类
| 工具名 | 功能 |
|--------|------|
| `analyze_slow_queries` | 分析慢查询 |
| `analyze_locks` | 分析锁等待和死锁 |
| `analyze_transactions` | 分析事务状态，查找长事务 |
| `configure_slow_query_log` | 配置慢查询日志 |

### 优化类
| 工具名 | 功能 |
|--------|------|
| `explain_query` | 分析 SQL 执行计划 |
| `analyze_config` | 分析配置参数 |
| `analyze_indexes` | 分析索引使用情况 |
| `get_index_statistics` | 获取表的索引统计信息 |
| `get_table_sizes` | 获取表大小信息 |

### 通用类
| 工具名 | 功能 |
|--------|------|
| `execute_query` | 执行 SQL 查询（仅 SELECT/SHOW/EXPLAIN） |
| `kill_connection` | 终止指定连接 |

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 运行
python app.py
```

## 环境变量配置

```env
# LLM 配置
ZHIPU_API_KEY=your_api_key
ZHIPU_MODEL=glm-4

# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=mysql
```

## 对话示例

```
你: 检查一下 MySQL 健康状态
Agent: [调用 health_check] 当前连接使用率 10/151，缓冲池命中率 99.5%，状态健康。

你: 分析一下慢查询
Agent: [调用 analyze_slow_queries] 发现 5 个慢查询，TOP1 执行时间 3.2 秒...

你: 帮我优化这个 SQL: SELECT * FROM orders WHERE customer_id = 100
Agent: [调用 explain_query] 发现全表扫描，建议在 customer_id 列添加索引...

你: 查看索引使用情况
Agent: [调用 analyze_indexes] 发现 3 个未使用的索引，建议删除...
```

## 注意事项

1. **安全性**: `execute_query` 仅支持 SELECT/SHOW/EXPLAIN，不允许执行修改操作
2. **权限**: 部分工具需要 SUPER 或 SYSTEM_VARIABLES_ADMIN 权限
3. **记忆**: 支持多轮对话记忆，输入 `clear` 清除历史
4. **退出**: 输入 `quit`、`exit` 或 `q` 退出程序

## 代码规范

- 使用 Python 3.10+ 语法（类型注解、match-case 等）
- 异步函数使用 `async/await`
- 日志使用 `utils.logger`
- 配置使用 `config.settings`
