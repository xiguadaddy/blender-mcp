"""
BlenderMCP插件全局变量

此模块包含BlenderMCP插件使用的全局变量和常量。
"""

# BlenderMCP版本
VERSION = "0.3.0"

# MCP服务器进程
mcp_server_process = None

# 全局设置
settings = {
    "debug_mode": False,
    "auto_start_server": True,
    "auto_connect": True
} 