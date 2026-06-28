"""
聊天相关的数据模型
"""
from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """聊天请求模型"""
    question: str
    thread_id: Optional[str] = None  # 对话线程ID，用于多轮对话和状态持久化


class ChatResponse(BaseModel):
    """聊天响应模型"""
    answer: str
    status: str = "completed"
    thread_id: Optional[str] = None  # 返回的对话线程ID