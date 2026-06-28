# LangGraph 多 Agent 研究助手

基于 **FastAPI + Vue 3 + LangGraph** 的多 Agent 研究助手示例项目。项目以最小可理解的工程结构实现了规划、研究、写作三个 Agent 的协作流程，并提供前后端分离的聊天界面、SSE 流式响应、多会话管理和 LangGraph checkpoint 持久化能力。

## 项目简介

本项目适合用于学习 LangGraph 多 Agent 工作流，也可以作为轻量级 Agent 应用脚手架继续扩展。相比完整生产级 Agent 系统，本项目保留核心链路，降低初学者理解成本。

### 核心功能

- **多 Agent 协作**：Planner 负责制定计划，Researcher 负责搜索与整理资料，Writer 负责生成最终回答
- **流式对话**：后端通过 SSE 实时推送计划、研究结果和最终答案
- **多会话管理**：使用 `thread_id` 隔离不同对话上下文
- **状态持久化**：LangGraph checkpoint 使用 SQLite 保存工作流状态
- **消息落库**：MySQL 保存会话列表、用户消息和 Agent 中间结果
- **工具调用**：Researcher 可调用 Tavily Web Search，也预留 MCP 工具接入能力
- **前后端分离**：FastAPI 提供 API，Vue 3 + Vite 提供聊天界面

## 技术架构

```text
┌─────────────────────────────────────────────────────────┐
│                    前端层 Vue 3 + Vite                  │
│  聊天窗口 / 会话列表 / Markdown 渲染 / SSE 流式读取       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────┴──────────────────────────────────┐
│                     API 层 FastAPI                       │
│  /api/chat / /api/chat/sync / 会话历史 / 消息读取 / 删除   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                 LangGraph 多 Agent 工作流                │
│  Planner → Researcher → Writer                           │
│  State / Node / Graph / Checkpointer                      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                       数据与工具层                        │
│  MySQL 会话消息 / SQLite Checkpoints / Tavily Search / MCP │
└─────────────────────────────────────────────────────────┘
```

## 技术栈

| 技术 | 说明 |
| --- | --- |
| FastAPI | 后端 Web 框架 |
| LangGraph | 多 Agent 工作流编排 |
| LangChain | LLM、消息、工具调用基础能力 |
| SQLite Checkpointer | LangGraph 状态快照持久化 |
| MySQL + SQLAlchemy | 会话和消息历史存储 |
| PyMySQL | MySQL Python 驱动 |
| Tavily | Web Search 工具 |
| Vue 3 + Vite | 前端框架与构建工具 |
| markdown-it | 前端 Markdown 渲染 |
| uv | Python 依赖与环境管理 |

## 项目结构

```text
Langgraph_Agent/
├── src/
│   ├── main.py                    # FastAPI 应用入口
│   ├── routes/
│   │   └── chat.py                # 聊天、会话、消息 API
│   ├── graph/
│   │   ├── state.py               # LangGraph State 定义
│   │   ├── nodes.py               # Planner / Researcher / Writer 节点
│   │   └── builder.py             # 工作流图构建
│   ├── prompts/                   # Agent 提示词模板
│   ├── tools/
│   │   └── tools.py               # Tavily 搜索工具
│   ├── database/
│   │   ├── database.py            # MySQL 连接配置
│   │   ├── models.py              # Conversation / Message 模型
│   │   └── checkpointer.py        # LangGraph SQLite checkpointer
│   └── mcp_agreement/             # MCP 工具接入示例
├── frontend/                      # Vue 3 前端
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   └── init_database.py           # 数据库建表脚本
├── pyproject.toml                 # Python 项目依赖
├── uv.lock                        # uv 锁定文件
└── README.md
```

## 快速开始

### 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 16+
- MySQL 8.0+
- 阿里云百炼 / DashScope 兼容 OpenAI API Key
- Tavily API Key，可选，用于联网搜索

### 1. 安装后端依赖

```bash
uv sync
```

### 2. 配置环境变量

在项目根目录创建 `.env`：

```env
MODEL_NAME=qwen3-max
DASHSCOPE_API_KEY=你的百炼_API_Key
ALIBABA_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
TAVILY_API_KEY=你的_Tavily_API_Key
CHECKPOINT_DB_PATH=checkpoints.db
```

数据库连接当前在 `src/database/database.py` 中配置：

```python
DATABASE_URL = "mysql+pymysql://root:123456@localhost/langgraph_agent_rag?charset=utf8mb4"
```

请根据本机 MySQL 用户名、密码和数据库名调整。

### 3. 初始化数据库

先确保 MySQL 中已创建数据库：

```sql
CREATE DATABASE langgraph_agent_rag DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

再执行建表脚本：

```bash
uv run python scripts/init_database.py
```

### 4. 启动后端

```bash
uv run uvicorn src.main:app --reload --port 8000
```

后端 API 文档：

```text
http://127.0.0.1:8000/docs
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端访问地址以 Vite 输出为准，通常是：

```text
http://127.0.0.1:5173
```

## 核心模块

### 1. LangGraph 工作流

核心流程位于 `src/graph/builder.py`：

```text
START → planner → researcher → writer → END
```

`planner` 生成研究计划，`researcher` 根据计划调用搜索工具并整理资料，`writer` 基于研究结果输出最终回答。

### 2. 状态管理

核心状态位于 `src/graph/state.py`，包括：

- `messages`：对话消息历史
- `task`：当前用户问题
- `plan`：规划器输出
- `research_results`：研究员输出
- `final_answer`：最终回答

### 3. 持久化

- MySQL 保存会话元数据和完整消息历史
- SQLite checkpoint 保存 LangGraph 状态快照
- 每次请求通过 `thread_id` 实现对话隔离和上下文恢复

### 4. SSE 流式响应

`/api/chat` 会按阶段返回：

- `start`：开始处理
- `plan`：研究计划
- `research`：研究结果
- `answer` / `final`：最终答案
- `done`：完成
- `error`：错误信息

## 常见问题

### 页面一直显示“处理中”怎么办？

优先查看后端终端日志。常见原因包括：模型 API Key 不正确、MySQL 未启动、Tavily 搜索超时或模型工具调用时间较长。

### `langgraph.checkpoint.sqlite` 找不到怎么办？

SQLite checkpointer 需要单独安装：

```bash
uv add langgraph-checkpoint-sqlite
```

### 如何更换模型？

修改 `.env` 中的 `MODEL_NAME`、`DASHSCOPE_API_KEY`、`ALIBABA_BASE_URL`。当前代码使用 OpenAI 兼容接口初始化模型。

### 如何添加新 Agent？

1. 在 `src/prompts/` 新增提示词
2. 在 `src/graph/nodes.py` 新增节点函数
3. 在 `src/graph/builder.py` 添加节点和边
4. 如需持久化新字段，同步更新 `src/graph/state.py`

### 如何添加新工具？

在 `src/tools/tools.py` 中使用 `@tool` 定义工具，并将其加入 `get_research_tools()` 返回列表。

## 参考资源

- [LangGraph 文档](https://docs.langchain.com/oss/python/langgraph)
- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Vue 3 文档](https://vuejs.org/)
