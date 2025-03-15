"""
BlenderMCP Server

This module provides the server implementation for BlenderMCP.
"""

import logging
from .core import BlenderMCPServer
from .handlers import BlenderCommandHandler

logger = logging.getLogger(__name__)

def create_server(host: str = "localhost", port: int = 9876) -> BlenderMCPServer:
    """创建并配置服务器实例
    
    Args:
        host: 服务器主机地址
        port: 服务器端口号
        
    Returns:
        BlenderMCPServer: 配置好的服务器实例
    """
    # 创建服务器实例
    server = BlenderMCPServer(host, port)
    
    # 创建命令处理器
    handler = BlenderCommandHandler()
    
    # 注册命令处理器
    for command, func in handler.get_handlers().items():
        server.register_handler(command, func)
        
    return server 