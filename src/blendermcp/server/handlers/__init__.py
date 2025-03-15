"""
BlenderMCP Command Handlers

This module registers all command handlers with the server.
"""

from typing import Dict, Any
from .blender_handler import BlenderCommandHandler
from ..server import BlenderMCPServer

def register_handlers(server: BlenderMCPServer):
    """Register all command handlers with the server"""
    
    # 注册对象操作命令
    server.command_registry.register(
        "create_object",
        BlenderCommandHandler.create_object
    )
    server.command_registry.register(
        "delete_object",
        BlenderCommandHandler.delete_object
    )
    
    # 注册材质操作命令
    server.command_registry.register(
        "set_material",
        BlenderCommandHandler.set_material
    )
    
    # 注册场景信息命令
    server.command_registry.register(
        "get_scene_info",
        BlenderCommandHandler.get_scene_info
    ) 