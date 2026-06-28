"""
数据库模型定义
"""
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class Conversation(Base):
    """
    对话会话表
    
    存储每个对话的基本信息，thread_id 对应 LangGraph 的 thread_id
    每个 thread_id 对应一个独立的对话历史，实现对话隔离
    """
    __tablename__ = "conversations"
    
    # thread_id 作为主键，对应 LangGraph 的 thread_id
    thread_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 对话标题（从第一条消息自动生成或用户自定义）
    title = Column(String(255), nullable=True)
    
    # 创建时间
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # 更新时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关联的消息列表
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    
    def __repr__(self):
        return f"<Conversation(thread_id={self.thread_id}, title={self.title})>"


class Message(Base):
    """
    消息表
    
    存储每个对话的完整消息历史记录，包括：
    - 用户消息
    - Agent 的中间结果（plan, research_results）
    - 最终答案
    """
    __tablename__ = "messages"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联的对话 thread_id
    thread_id = Column(String(36), ForeignKey('conversations.thread_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 消息类型：user, assistant, plan, research, answer, system
    role = Column(String(20), nullable=False, index=True)
    
    # 消息内容
    content = Column(Text, nullable=False)
    
    # 节点类型（如果是 Agent 生成的消息）：planner, researcher, writer
    node_type = Column(String(50), nullable=True)
    
    # 创建时间
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # 关联的对话对象
    conversation = relationship("Conversation", back_populates="messages")
    
    # 创建复合索引，优化查询性能
    __table_args__ = (
        Index('idx_thread_created', 'thread_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, thread_id={self.thread_id}, role={self.role})>"
