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

# 尝试导入bpy模块
try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

import os
import logging
import tempfile
from . import preferences
from . import server_operators
if HAS_BPY:
    from . import panels
    from . import tool_viewer
from . import executor  # 确保导入执行器

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
logger = logging.getLogger("BlenderMCP.Addon")

# 注册和注销函数
def register():
    """注册所有addon模块"""
    logger.info("注册BlenderMCP addon模块")
    
    # 注册首选项
    preferences.register()
    
    # 注册服务器操作符
    server_operators.register()
    
    if HAS_BPY:
        # 注册面板
        panels.register()
        
        # 注册工具查看器
        tool_viewer.register()
        
        # 初始化执行器
        executor.initialize()
        
        # 自动启动服务器
        try:
            addon_prefs = preferences.get_addon_preferences(bpy.context)
            if addon_prefs.auto_start_server:
                logger.info("自动启动MCP服务器")
                mode = addon_prefs.server_mode
                
                if mode == 'WEBSOCKET':
                    host = addon_prefs.websocket_host
                    port = addon_prefs.websocket_port
                    server_operators.start_server(mode, host, port)
                else:
                    server_operators.start_server(mode)
        except Exception as e:
            logger.error(f"自动启动MCP服务器失败: {str(e)}")

    # 启动请求监听器
    from . import request_listener
    request_listener.start()

def unregister():
    """注销所有addon模块"""
    logger.info("注销BlenderMCP addon模块")
    
    # 停止服务器
    if server_operators.is_server_running():
        logger.info("停止MCP服务器")
        server_operators.stop_server()
    
    if HAS_BPY:
        # 注销工具查看器
        tool_viewer.unregister()
        
        # 注销面板
        panels.unregister()
    
    # 注销服务器操作符
    server_operators.unregister()
    
    # 注销首选项
    preferences.unregister()

    # 停止请求监听器
    from . import request_listener
    request_listener.stop()

# 允许直接运行脚本
if __name__ == "__main__":
    register() 