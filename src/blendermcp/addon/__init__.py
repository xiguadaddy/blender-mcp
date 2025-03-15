"""
BlenderMCP Addon - Blender Multi-Client Protocol
"""

bl_info = {
    "name": "BlenderMCP",
    "author": "Your Name",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),  # 支持Blender 2.80及以上版本
    "location": "Preferences -> Add-ons",
    "description": "Blender Multi-Client Protocol - 允许外部程序通过WebSocket控制Blender",
    "warning": "",
    "doc_url": "",
    "category": "Development",
}

import bpy
import logging
import os
import sys

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加父目录到sys.path
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 导入模块
from blendermcp.server.handlers import register_handlers
from .preferences import BlenderMCPAddonPreferences
from .server_operators import BLENDERMCP_OT_start_server, BLENDERMCP_OT_stop_server, server
from .properties import *
from .operators import *
from .panels import *

def register():
    """注册插件"""
    logger.info("正在注册 BlenderMCP 插件...")
    try:
        bpy.utils.register_class(BlenderMCPAddonPreferences)
        bpy.utils.register_class(BLENDERMCP_OT_start_server)
        bpy.utils.register_class(BLENDERMCP_OT_stop_server)
        
        # 注册属性
        register_properties()
        
        # 注册操作符
        register_operators()
        
        # 注册面板
        register_panels()
        
        # 注册处理器
        if server:
            register_handlers(server)
        
        # 如果设置了自动启动，则启动服务器
        preferences = bpy.context.preferences.addons["blendermcp"].preferences
        if preferences.auto_start:
            bpy.ops.blendermcp.start_server()
        
        logger.info("BlenderMCP 插件注册完成")
    except Exception as e:
        logger.error(f"插件注册失败: {str(e)}")
        raise

def unregister():
    """注销插件"""
    logger.info("正在注销 BlenderMCP 插件...")
    try:
        # 确保服务器已停止
        if hasattr(bpy.ops.blendermcp, "stop_server"):
            bpy.ops.blendermcp.stop_server()
        
        # 注销属性
        unregister_properties()
        
        # 注销操作符
        unregister_operators()
        
        # 注销面板
        unregister_panels()
        
        bpy.utils.unregister_class(BLENDERMCP_OT_stop_server)
        bpy.utils.unregister_class(BLENDERMCP_OT_start_server)
        bpy.utils.unregister_class(BlenderMCPAddonPreferences)
        
        logger.info("BlenderMCP 插件注销完成")
    except Exception as e:
        logger.error(f"插件注销失败: {str(e)}")
        raise

if __name__ == "__main__":
    register() 