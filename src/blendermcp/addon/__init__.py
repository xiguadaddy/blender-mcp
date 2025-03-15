"""
BlenderMCP插件

该插件提供了在Blender中使用MCP协议的功能。
"""

bl_info = {
    "name": "BlenderMCP",
    "author": "BlenderMCP Team",
    "description": "Blender插件，用于与MCP协议通信",
    "blender": (3, 0, 0),
    "version": (0, 1, 0),
    "location": "View3D > Sidebar > MCP",
    "category": "AI"
}

# 阻止asyncio导入，避免与Blender内置Python版本的兼容性问题
import sys
sys.modules['asyncio'] = None

# 导入必要的模块
import bpy
import os
import logging
import tempfile
from . import preferences
from . import panels
from . import server_operators

# 配置日志
log_file = os.path.join(tempfile.gettempdir(), "blendermcp_addon.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 注册和注销函数
def register():
    logger.info("注册BlenderMCP插件")
    
    # 注册首选项
    preferences.register()
    
    # 注册服务器操作符
    server_operators.register()
    
    # 注册面板
    panels.register()
    
    # 自动启动服务器
    try:
        addon_prefs = bpy.context.preferences.addons["blendermcp"].preferences
        if addon_prefs.auto_start:
            logger.info("自动启动MCP服务器")
            bpy.ops.mcp.start_server()
    except Exception as e:
        logger.error(f"自动启动MCP服务器时出错: {str(e)}", exc_info=True)

def unregister():
    logger.info("注销BlenderMCP插件")
    
    # 停止服务器
    if server_operators.is_server_running():
        logger.info("停止MCP服务器")
        server_operators.stop_mcp_server_process()
    
    # 注销面板
    panels.unregister()
    
    # 注销服务器操作符
    server_operators.unregister()
    
    # 注销首选项
    preferences.unregister()

# 允许直接运行脚本
if __name__ == "__main__":
    register() 