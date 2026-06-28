"""
MCP (Model Context Protocol) 服务模块

提供MCP客户端和服务器功能，用于集成外部工具和服务。
"""

from .multi_mcp import get_mcp_tools, mcp_client

__all__ = ["get_mcp_tools", "mcp_client"]
