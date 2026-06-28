import asyncio
import os
import threading
import queue

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import StructuredTool

mcp_client = MultiServerMCPClient(
    {
        "WebSearch": {
            "transport": "sse",
            "url": "https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse",
            "headers": {"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"},
        },
        "Amap Maps": {
            "transport": "sse",
            "url": "https://dashscope.aliyuncs.com/api/v1/mcps/amap-maps/sse",
            "headers": {"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"},
        },
        # "Time": {
        #     "transport": "sse",
        #     "url": "https://dashscope.aliyuncs.com/api/v1/mcps/TimeZone/sse",
        #     "headers": {"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"},
        # },
        # "12306": {
        #     "transport": "sse",
        #     "url": "https://dashscope.aliyuncs.com/api/v1/mcps/china-railway/sse",
        #     "headers": {"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"},
        # },
    }
)

_mcp_tools_cache = None

def _run_async_in_thread(coro):
    """在新线程中运行异步函数"""
    result_queue = queue.Queue()
    exception_queue = queue.Queue()
    
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            result = new_loop.run_until_complete(coro)
            result_queue.put(result)
        except Exception as e:
            exception_queue.put(e)
        finally:
            new_loop.close()
    
    thread = threading.Thread(target=run_in_new_loop)
    thread.start()
    thread.join()
    
    if not exception_queue.empty():
        raise exception_queue.get()
    return result_queue.get()


def _wrap_async_tool(tool):
    """将异步工具包装成同步工具"""
    if not hasattr(tool, 'ainvoke'):
        return tool
    
    def sync_invoke(**kwargs):
        input_dict = kwargs.copy()
        run_manager = input_dict.pop('run_manager', None)
        
        try:
            # 尝试检测是否有运行中的事件循环
            try:
                asyncio.get_running_loop()
                # 如果有运行中的循环，在新线程中运行
                result = _run_async_in_thread(tool.ainvoke(input_dict, run_manager))
            except RuntimeError:
                # 没有运行中的循环，直接运行
                result = asyncio.run(tool.ainvoke(input_dict, run_manager))
            
            # 简单格式化：如果是列表，提取text字段；否则转为字符串
            if isinstance(result, list) and result and isinstance(result[0], dict):
                texts = [str(item.get('text', item)) for item in result]
                return "\n".join(texts) if texts else str(result)
            return str(result) if not isinstance(result, str) else result
            
        except Exception as e:
            # 捕获所有异常，返回错误信息而不是抛出异常
            error_type = type(e).__name__
            error_msg = str(e)
            
            # 处理常见的错误类型
            if "SSEError" in error_type or "text/event-stream" in error_msg:
                return f"错误：MCP 服务器连接失败，响应格式不正确。请检查服务器状态和配置。"
            elif "ConnectTimeout" in error_type or "timeout" in error_msg.lower():
                return f"错误：连接超时，无法连接到 MCP 服务器。"
            elif "ConnectError" in error_type:
                return f"错误：无法连接到 MCP 服务器。"
            else:
                return f"错误：工具调用失败 ({error_type}): {error_msg}"
    
    return StructuredTool(
        name=tool.name,
        description=tool.description,
        func=sync_invoke,
        args_schema=tool.args_schema if hasattr(tool, 'args_schema') else None,
    )


def get_mcp_tools():
    """获取 MCP 工具列表，包装成同步工具"""
    global _mcp_tools_cache
    if _mcp_tools_cache is not None:
        return _mcp_tools_cache
    
    try:
        asyncio.get_running_loop()
        raw_tools = _run_async_in_thread(mcp_client.get_tools())
    except RuntimeError:
        raw_tools = asyncio.run(mcp_client.get_tools())
    
    _mcp_tools_cache = [_wrap_async_tool(tool) for tool in raw_tools]
    return _mcp_tools_cache
