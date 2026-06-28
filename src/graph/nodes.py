"""
节点定义 - 每个 Agent 的具体实现

每个节点就是一个函数：
- 输入: State (当前状态)
- 输出: dict (要更新的状态字段)
"""

import os
from pathlib import Path
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from .state import State
from ..tools.tools import get_research_tools
from ..mcp_agreement.multi_mcp import get_mcp_tools

## 读取模型api 选择自己的模型 这里用的是百炼平台提供的大模型api
MODEL_NAME=os.getenv("MODEL_NAME")
ALIBABA_BASE_URL = os.getenv("ALIBABA_BASE_URL")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

model = init_chat_model(
    MODEL_NAME,  # 1. 模型名称：请在百炼控制台确认准确的 model ID
    model_provider="openai",  # 2. 提供商：必须填 openai
    base_url=ALIBABA_BASE_URL,  # 3. 地址：百炼的兼容入口
    api_key=DASHSCOPE_API_KEY,  # 4. 你的百炼 / DashScope API Key
)

def format_conversation_history(
    state: State,
    max_turns: int = 10,
    max_chars: int = 2000,
) -> str:
    """
    将同一 thread_id 的历史对话整理成一段简洁文本，供各个 Agent 作为“记忆”使用。

    - 只截取最近 max_turns 轮（用户 + 助手）
    - 控制总长度不超过 max_chars，避免 prompt 过长
    """
    messages = state.get("messages", []) or []
    if not messages:
        return "（暂无历史对话，仅根据当前问题回答。）"

    useful_msgs = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            role = "用户"
        elif isinstance(msg, AIMessage):
            role = "助手"
        elif isinstance(msg, SystemMessage):
            role = "系统"
        else:
            # ToolMessage 等先跳过，避免干扰提示词
            continue
        useful_msgs.append((role, str(msg.content)))

    if not useful_msgs:
        return "（暂无可用的历史轮次，仅根据当前问题回答。）"

    # 只保留最近若干条，再恢复成按时间顺序的文本
    trimmed = list(reversed(useful_msgs))
    trimmed = trimmed[: max_turns * 2]
    trimmed.reverse()

    lines = [f"{role}: {content}" for role, content in trimmed]
    history_text = "\n".join(lines)

    if len(history_text) > max_chars:
        history_text = "……(历史对话已截断，仅保留最近片段)\n" + history_text[-max_chars:]

    return history_text


def load_prompt(name: str) -> str:
    """加载提示词文件"""
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return ""


# ============================================================
# 节点实现
# ============================================================

def planner_node(state: State) -> dict:
    """
    规划器节点 - 制定研究计划
    输入: 用户的任务
    输出: 执行计划
    """
    print("\n🎯 [规划器] 正在制定计划...")
    
    llm = model
    system_prompt = load_prompt("planner")
    history_text = format_conversation_history(state)
    
    # print(f"历史对话：{history_text}。")
    
    # 构建消息
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""
历史对话（最近若干轮，供你理解上下文）:
{history_text}

当前任务:
{state['task']}

请为“当前任务”制定研究计划，并确保与历史对话上下文一致。
""".strip())
    ]
    
    # 调用 LLM
    response = llm.invoke(messages)
    plan = response.content
    
    print(f"📋 计划已生成:\n{plan}\n")
    
    # 返回要更新的状态
    return {
        "plan": plan,
    }


def researcher_node(state: State) -> dict:
    """
    研究员节点 - 搜索和收集信息
    
    输入: 执行计划
    输出: 研究结果
    """
    print("\n🔍 [研究员] 正在收集信息...")
    
    system_prompt = load_prompt("researcher")
    history_text = format_conversation_history(state)
    
    # print(f"历史对话：{history_text}。")
    
    # 绑定工具和mcp到 LLM
    tools = get_research_tools()
    # mcp_tools = get_mcp_tools()
    # llm = model.bind_tools(tools)
    llm_with_tools = model.bind_tools(tools)
    
    # 构建消息
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""
历史对话（最近若干轮，供你理解上下文）:
{history_text}

任务: {state['task']}

研究计划:
{state['plan']}

请根据计划搜索相关信息。
""")
    ]
    
    # 第一次调用 - LLM 决定是否使用工具
    response = llm_with_tools.invoke(messages)

    # 如果 LLM 想要调用工具（最多循环若干轮，避免无限调用）
    max_tool_rounds = 5
    tool_round = 0
    consecutive_failures = 0  # 连续失败次数
    max_consecutive_failures = 2  # 最大连续失败次数
    called_tools = set()  # 记录已调用的工具，避免重复调用
    
    while response.tool_calls and tool_round < max_tool_rounds:
        tool_round += 1
        tool_names = [tc['name'] for tc in response.tool_calls]
        print(f"🔧 调用工具: {tool_names}")

        # 检查是否有重复调用
        current_tool_key = tuple(sorted(tool_names))
        if current_tool_key in called_tools:
            print(f"⚠️ 检测到重复工具调用，停止循环以避免无限重试")
            break
        called_tools.add(current_tool_key)

        # 先把 assistant 的响应加入消息列表
        messages.append(response)

        # 执行每个工具调用，并用 ToolMessage 返回结果
        all_success = True
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]  # 获取 tool_call_id

            # 找到并执行对应的工具
            result = "工具未找到"
            try:
                tool_found = False
                for tool in tools:
                    if tool.name == tool_name:
                        tool_found = True
                        result = tool.invoke(tool_args)
                        break
                
                if not tool_found:
                    result = f"错误：未找到工具 '{tool_name}'"
                    all_success = False
                elif result is None or (isinstance(result, str) and result.startswith("错误")):
                    all_success = False
                    
            except Exception as e:
                error_msg = f"工具调用失败：{str(e)}"
                print(f"❌ {error_msg}")
                result = error_msg
                all_success = False

            # 使用 ToolMessage 返回结果（必须指定 tool_call_id）
            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                )
            )

        # 如果所有工具调用都失败，增加失败计数
        if not all_success:
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                print(f"⚠️ 连续失败 {consecutive_failures} 次，停止工具调用循环")
                # 添加一个提示消息，告诉 LLM 工具调用失败，应该停止
                messages.append(
                    AIMessage(content="工具调用连续失败，请基于已有信息给出研究结果，不要再调用工具。")
                )
                break
        else:
            consecutive_failures = 0  # 重置失败计数

        # 下一轮：让 LLM 基于工具返回继续（可能继续调用工具，或直接给出结论）
        response = llm_with_tools.invoke(messages)
    
    research_results = response.content
    print(f"📚 研究完成，收集到信息\n")
    
    return {
        "research_results": research_results,
    }


def writer_node(state: State) -> dict:
    """
    写作者节点 - 生成最终答案
    
    输入: 研究结果
    输出: 最终答案
    """
    print("\n✍️ [写作者] 正在撰写答案...")
    
    llm = model
    system_prompt = load_prompt("writer")
    history_text = format_conversation_history(state)
    # print(f"历史对话：{history_text}。")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""
历史对话（最近若干轮，供你理解上下文）:
{history_text}

用户问题: {state['task']}

研究结果:
{state['research_results']}

请根据以上研究结果，撰写一份完整的回答。
""")
    ]
    
    response = llm.invoke(messages)
    final_answer = response.content
    
    print(f"✅ 答案已生成\n")
    
    return {
        "final_answer": final_answer,
        "messages": [response]
    }
