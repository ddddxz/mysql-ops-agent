# MySQL 智能运维平台

基于 LangGraph 多智能体架构的 MySQL 运维助手，集成 RAG 知识库和 MCP 工具协议。

## 功能特性

- **自然语言交互**: 通过对话方式管理 MySQL 数据库
- **多智能体协作**: 监控、诊断、优化等专业智能体
- **RAG 知识增强**: 内置 MySQL 运维知识库
- **流式输出**: 实时显示 AI 思考过程
- **健康报表**: 自动生成数据库健康报告
- **定时任务**: 支持定时健康检查和报表生成
- **角色权限**: JWT 认证 + 角色权限控制

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Element Plus + Pinia + Vite |
| 后端 | FastAPI + LangChain + LangGraph |
| AI | 通义千问 (qwen-plus) + RAG |
| 工具协议 | MCP (Model Context Protocol) |
| 数据库 | MySQL |
| 向量存储 | Chroma |

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+

### 2. 后端配置

```bash
# 克隆项目
git clone https://github.com/ddddxz/mysql-ops-agent.git
cd mysql-ops-agent

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入实际配置

# 设置 API Key
export DASHSCOPE_API_KEY=your_api_key
```

### 3. 前端配置

```bash
cd frontend
npm install
```

### 4. 启动服务

```bash
# 启动后端 (在项目根目录)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端 (在 frontend 目录)
npm run dev
```

访问 http://localhost:3000 即可使用。

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| root | (通过 DEFAULT_ROOT_PASSWORD 设置) | admin |
| admin | admin123 | admin |
| operator | oper123 | operator |
| viewer | view123 | viewer |

## ⚠️ 安全提示

**生产环境部署前，请务必：**

1. **修改默认密码**: 通过 `DEFAULT_ROOT_PASSWORD` 环境变量设置 root 密码
2. **修改其他账号密码**: 首次登录后立即修改 admin、operator、viewer 密码
3. **保护敏感配置**: 
   - `.env` 文件包含敏感信息，**切勿提交到版本控制**
   - 确保 `.env` 已在 `.gitignore` 中
4. **API Key 安全**: 通过环境变量 `DASHSCOPE_API_KEY` 设置，不要硬编码
5. **数据库权限**: 生产环境使用最小权限原则，避免使用 root 账号连接数据库
6. **HTTPS**: 生产环境务必启用 HTTPS

## 项目结构

```
mysql-ops-agent/
├── api/                 # FastAPI 路由
├── agent/               # LangGraph 智能体
├── config/              # 配置管理
├── db/                  # 数据库模型
├── frontend/            # Vue3 前端
├── knowledge/           # RAG 知识库文档
├── model/               # LLM 封装
├── rag/                 # RAG 检索增强
├── scheduler/           # 定时任务
├── utils/               # 工具函数
├── .env.example         # 环境变量示例
└── requirements.txt     # Python 依赖
```

## License

MIT License
