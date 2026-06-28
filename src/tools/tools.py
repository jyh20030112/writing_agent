"""
工具定义 - Agent 可以调用的外部能力

工具让 Agent 能够与外部世界交互，比如搜索网络、执行代码等。
"""

import os
from langchain_core.tools import tool

@tool
def web_search(query: str) -> str:
    """
    搜索网络获取信息。
    Args:
        query: 搜索关键词
        
    Returns:
        搜索结果摘要
    """
    # 检查是否配置了 Tavily API
    api_key = os.getenv("TAVILY_API_KEY")
    
    if api_key:
        # 使用 Tavily 搜索
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(query, max_results=5)
            
            # 格式化结果
            results = []
            for item in response.get("results", []):
                results.append(f"**{item['title']}**\n{item['content']}\n来源: {item['url']}\n")
            
            return "\n---\n".join(results) if results else "未找到相关结果"
        except Exception as e:
            return f"搜索出错: {str(e)}"
    else:
        return f"没有配置 API"


# 导出所有工具
def get_research_tools():
    """
    获取研究员可用的工具列表
    
    包括:
    - 自定义工具（如web_search）
    """
    tools = [web_search]
    
    return tools



