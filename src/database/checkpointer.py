"""
Checkpointer for LangGraph - 状态持久化

使用 SQLite 存储 LangGraph 的 checkpoints（状态快照）。
对话元数据可以存储在 MySQL 中（通过 models.py 中的 Conversation 模型）。
"""
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

# SQLite 数据库文件路径
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "checkpoints.db")

@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncSqliteSaver, None]:
    """
    获取 checkpointer 实例（异步上下文管理器）
    
    使用方式:
        async with get_checkpointer() as checkpointer:
            graph = build_graph(checkpointer=checkpointer)
            # 使用 graph...
    
    这样可以确保 checkpointer 在使用后正确关闭。
    
    注意：AsyncSqliteSaver.from_conn_string() 返回的就是一个异步上下文管理器，
    它会自动处理 setup 和 cleanup，不需要手动调用 setup()。
    """
    # AsyncSqliteSaver.from_conn_string() 返回的就是一个异步上下文管理器
    # 直接使用它，不需要手动调用 setup()
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as checkpointer:
        yield checkpointer
