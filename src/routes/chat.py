"""
聊天相关的路由处理
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json
import uuid
from typing import List, Optional
from datetime import datetime

# 加载环境变量
load_dotenv()

from src.graph.builder import build_graph
from src.schemas.chat import ChatRequest, ChatResponse
from src.database.checkpointer import get_checkpointer
from src.database.database import get_db, SessionLocal
from src.database.models import Conversation, Message
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_class=StreamingResponse)
async def chat(request: ChatRequest):
    """
    聊天接口 - 流式返回结果（支持持久化对话）
    
    使用 Server-Sent Events (SSE) 格式返回流式数据。
    如果提供了 thread_id，会使用持久化状态，支持多轮对话。
    """
    question = request.question.strip()
    
    if not question:
        async def error_generator():
            yield f"data: {json.dumps({'error': '问题不能为空'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
    
    # 如果没有提供 thread_id，生成一个新的
    thread_id = request.thread_id or f"thread-{uuid.uuid4().hex[:8]}"
    
    # 如果是新对话，保存到数据库
    if not request.thread_id:
        db = SessionLocal()
        try:
            # 检查是否已存在
            existing = db.query(Conversation).filter(Conversation.thread_id == thread_id).first()
            if not existing:
                # 创建新对话记录，标题使用问题的前50个字符
                title = question[:50] if len(question) > 50 else question
                conversation = Conversation(
                    thread_id=thread_id,
                    title=title
                )
                db.add(conversation)
                db.commit()
        except Exception as e:
            db.rollback()
            # 记录错误但不中断流程
            print(f"保存对话记录失败: {e}")
        finally:
            db.close()
    else:
        # 更新现有对话的更新时间
        db = SessionLocal()
        try:
            conversation = db.query(Conversation).filter(Conversation.thread_id == thread_id).first()
            if conversation:
                conversation.updated_at = datetime.now()
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"更新对话记录失败: {e}")
        finally:
            db.close()
    
    async def generate_response():
        """生成流式响应"""
        try:
            # 使用 checkpointer 构建图（支持持久化）
            async with get_checkpointer() as checkpointer:
                graph = build_graph(checkpointer=checkpointer)
                
                # 配置：使用 thread_id 进行状态管理（实现对话隔离）
                config = {"configurable": {"thread_id": thread_id}}
                
                # 1. 先获取已有状态（如果有的话）
                existing_state_result = await graph.aget_state(config)
                existing_state = existing_state_result.values if existing_state_result else {}
                
                # 2. 构建新状态：基于已有状态更新，而不是覆盖
                # 获取已有的消息历史
                existing_messages = existing_state.get("messages", [])
                
                # 添加用户的新消息到历史中
                user_message = HumanMessage(content=question)
                updated_messages = existing_messages + [user_message]
                
                # 保存用户消息到数据库
                db = SessionLocal()
                try:
                    db_message = Message(
                        thread_id=thread_id,
                        role="user",
                        content=question,
                        node_type=None
                    )
                    db.add(db_message)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"保存用户消息失败: {e}")
                finally:
                    db.close()
                
                # 3. 构建初始状态（保留已有状态，只更新 task 和 messages）
                initial_state = {
                    "messages": updated_messages,  # 保留历史消息
                    "task": question,  # 当前任务
                    "plan": existing_state.get("plan", ""),  # 保留已有计划
                    "research_results": existing_state.get("research_results", ""),  # 保留已有研究结果
                    "final_answer": existing_state.get("final_answer", "")  # 保留已有答案
                }
                
                # 发送开始信号（包含 thread_id）
                yield f"data: {json.dumps({'type': 'start', 'message': '开始处理问题...', 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
                
                # 运行工作流并流式返回状态
                final_state = None
                plan_content = None
                research_content = None
                answer_content = None
                
                async for state in graph.astream(initial_state, config):
                    final_state = state
                    
                    # 发送当前状态更新
                    for node_name, node_state in state.items():
                        if node_name == "planner" and node_state.get("plan"):
                            plan_content = node_state.get("plan", "")
                            yield f"data: {json.dumps({'type': 'plan', 'content': plan_content}, ensure_ascii=False)}\n\n"
                            
                            # 保存计划到数据库
                            db = SessionLocal()
                            try:
                                db_message = Message(
                                    thread_id=thread_id,
                                    role="plan",
                                    content=plan_content,
                                    node_type="planner"
                                )
                                db.add(db_message)
                                db.commit()
                            except Exception as e:
                                db.rollback()
                                print(f"保存计划消息失败: {e}")
                            finally:
                                db.close()
                                
                        elif node_name == "researcher" and node_state.get("research_results"):
                            research_content = node_state.get("research_results", "")
                            yield f"data: {json.dumps({'type': 'research', 'content': research_content}, ensure_ascii=False)}\n\n"
                            
                            # 保存研究结果到数据库
                            db = SessionLocal()
                            try:
                                db_message = Message(
                                    thread_id=thread_id,
                                    role="research",
                                    content=research_content,
                                    node_type="researcher"
                                )
                                db.add(db_message)
                                db.commit()
                            except Exception as e:
                                db.rollback()
                                print(f"保存研究结果失败: {e}")
                            finally:
                                db.close()
                                
                        elif node_name == "writer" and node_state.get("final_answer"):
                            answer_content = node_state.get("final_answer", "")
                            yield f"data: {json.dumps({'type': 'answer', 'content': answer_content}, ensure_ascii=False)}\n\n"
                
                # 获取最终答案并保存
                if final_state and "writer" in final_state:
                    answer = final_state["writer"].get("final_answer", "")
                    if answer:
                        yield f"data: {json.dumps({'type': 'final', 'content': answer}, ensure_ascii=False)}\n\n"
                        
                        # 保存最终答案到数据库
                        db = SessionLocal()
                        try:
                            db_message = Message(
                                thread_id=thread_id,
                                role="assistant",
                                content=answer,
                                node_type="writer"
                            )
                            db.add(db_message)
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            print(f"保存最终答案失败: {e}")
                        finally:
                            db.close()
                
                # 发送完成信号（包含 thread_id）
                yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_msg = str(e)
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/chat/sync")
async def chat_sync(request: ChatRequest):
    """
    同步聊天接口 - 等待完整结果后返回（支持持久化对话）
    
    如果提供了 thread_id，会使用持久化状态，支持多轮对话。
    """
    question = request.question.strip()
    
    if not question:
        return ChatResponse(answer="问题不能为空", status="error", thread_id=None)
    
    # 如果没有提供 thread_id，生成一个新的
    thread_id = request.thread_id or f"thread-{uuid.uuid4().hex[:8]}"
    
    try:
        # 使用 checkpointer 构建图（支持持久化）
        async with get_checkpointer() as checkpointer:
            graph = build_graph(checkpointer=checkpointer)
            
            # 配置：使用 thread_id 进行状态管理（实现对话隔离）
            config = {"configurable": {"thread_id": thread_id}}
            
            # 1. 先获取已有状态（如果有的话）
            existing_state_result = await graph.aget_state(config)
            existing_state = existing_state_result.values if existing_state_result else {}
            
            # 2. 构建新状态：基于已有状态更新
            existing_messages = existing_state.get("messages", [])
            user_message = HumanMessage(content=question)
            updated_messages = existing_messages + [user_message]
            
            # 保存用户消息到数据库
            db = SessionLocal()
            try:
                db_message = Message(
                    thread_id=thread_id,
                    role="user",
                    content=question,
                    node_type=None
                )
                db.add(db_message)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"保存用户消息失败: {e}")
            finally:
                db.close()
            
            # 3. 构建初始状态（保留已有状态）
            initial_state = {
                "messages": updated_messages,
                "task": question,
                "plan": existing_state.get("plan", ""),
                "research_results": existing_state.get("research_results", ""),
                "final_answer": existing_state.get("final_answer", "")
            }
            
            # 运行工作流
            final_state = None
            async for state in graph.astream(initial_state, config):
                final_state = state
                
                # 保存中间结果到数据库
                db = SessionLocal()
                try:
                    for node_name, node_state in state.items():
                        if node_name == "planner" and node_state.get("plan"):
                            db_message = Message(
                                thread_id=thread_id,
                                role="plan",
                                content=node_state.get("plan", ""),
                                node_type="planner"
                            )
                            db.add(db_message)
                        elif node_name == "researcher" and node_state.get("research_results"):
                            db_message = Message(
                                thread_id=thread_id,
                                role="research",
                                content=node_state.get("research_results", ""),
                                node_type="researcher"
                            )
                            db.add(db_message)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"保存中间结果失败: {e}")
                finally:
                    db.close()
            
            # 获取最终答案
            answer = ""
            if final_state and "writer" in final_state:
                answer = final_state["writer"].get("final_answer", "")
                
                # 保存最终答案到数据库
                if answer:
                    db = SessionLocal()
                    try:
                        db_message = Message(
                            thread_id=thread_id,
                            role="assistant",
                            content=answer,
                            node_type="writer"
                        )
                        db.add(db_message)
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        print(f"保存最终答案失败: {e}")
                    finally:
                        db.close()
            
            return ChatResponse(answer=answer, status="completed", thread_id=thread_id)
        
    except Exception as e:
        return ChatResponse(answer=f"处理出错: {str(e)}", status="error", thread_id=thread_id)


@router.get("/chat/threads")
async def get_threads(db: Session = Depends(get_db)):
    """
    获取所有对话线程列表
    """
    try:
        # 从数据库获取所有对话
        conversations = db.query(Conversation).order_by(desc(Conversation.updated_at)).all()
        
        threads = []
        for conv in conversations:
            threads.append({
                "threadId": conv.thread_id,
                "title": conv.title or "新对话",
                "lastUpdate": conv.updated_at.isoformat() if conv.updated_at else datetime.now().isoformat(),
                "createdAt": conv.created_at.isoformat() if conv.created_at else datetime.now().isoformat()
            })
        
        return {"threads": threads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")


@router.get("/chat/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, db: Session = Depends(get_db)):
    """
    获取指定对话的完整消息历史
    
    优先从数据库的 Message 表读取完整记录，如果没有则从 checkpointer 状态中提取
    """
    try:
        # 1. 优先从数据库读取完整消息历史（保留完整记录）
        db_messages = db.query(Message).filter(
            Message.thread_id == thread_id
        ).order_by(Message.created_at.asc()).all()
        
        if db_messages:
            messages = []
            for msg in db_messages:
                # 将 role="assistant" 映射为 type="answer"，以便前端正确识别和渲染
                msg_type = msg.role
                if msg.role == "assistant":
                    msg_type = "answer"
                
                messages.append({
                    "type": msg_type,
                    "content": msg.content,
                    "node_type": msg.node_type,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else datetime.now().isoformat()
                })
            return {"messages": messages, "thread_id": thread_id, "source": "database"}
        
        # 2. 如果数据库中没有，尝试从 checkpointer 状态中提取（向后兼容）
        async with get_checkpointer() as checkpointer:
            from ..graph.builder import build_graph

            graph = build_graph(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": thread_id}}
            
            state_result = await graph.aget_state(config)
            
            messages = []
            
            if state_result and state_result.values:
                state = state_result.values
                
                # 提取各种状态字段
                if state.get("task"):
                    messages.append({
                        "type": "user",
                        "content": state.get("task", ""),
                        "timestamp": datetime.now().isoformat()
                    })
                
                if state.get("plan"):
                    messages.append({
                        "type": "plan",
                        "content": state.get("plan", ""),
                        "timestamp": datetime.now().isoformat()
                    })
                
                if state.get("research_results"):
                    messages.append({
                        "type": "research",
                        "content": state.get("research_results", ""),
                        "timestamp": datetime.now().isoformat()
                    })
                
                if state.get("final_answer"):
                    messages.append({
                        "type": "answer",
                        "content": state.get("final_answer", ""),
                        "timestamp": datetime.now().isoformat()
                    })
            
            return {"messages": messages, "thread_id": thread_id, "source": "checkpointer"}
            
    except Exception as e:
        # 如果都失败了，返回空列表而不是错误
        print(f"获取消息失败: {str(e)}")
        return {"messages": [], "thread_id": thread_id, "source": "error"}


@router.delete("/chat/threads/{thread_id}")
async def delete_thread(thread_id: str, db: Session = Depends(get_db)):
    """
    删除指定的对话线程
    
    由于 Conversation 和 Message 设置了 CASCADE 删除，删除 Conversation 会自动删除所有关联的 Message
    """
    try:
        # 从 MySQL 删除对话记录（CASCADE 会自动删除关联的 Message）
        conversation = db.query(Conversation).filter(Conversation.thread_id == thread_id).first()
        if conversation:
            db.delete(conversation)
            db.commit()
        
        # 注意：SQLite checkpointer 中的状态不会被自动删除
        # 如果需要完全清理，可以考虑：
        # 1. 定期清理旧的 checkpoints
        # 2. 或者直接操作 SQLite 数据库删除对应的记录
        
        return {"message": "对话已删除", "thread_id": thread_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")
