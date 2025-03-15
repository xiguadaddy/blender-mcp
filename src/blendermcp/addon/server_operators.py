"""
BlenderMCP Server Operators
"""

import bpy
import logging
from bpy.types import Operator
from ..server.server import BlenderMCPServer
from ..server.handlers import register_handlers

logger = logging.getLogger(__name__)

# 全局变量
server = None
is_server_running = False  # 新增：服务器状态标志

class BLENDERMCP_OT_start_server(Operator):
    """启动 BlenderMCP 服务器"""
    bl_idname = "blendermcp.start_server"
    bl_label = "Start Server"
    bl_description = "Start the BlenderMCP server"
    
    def execute(self, context):
        global server, is_server_running
        try:
            if is_server_running:
                self.report({'WARNING'}, "服务器已经在运行中")
                return {'CANCELLED'}
                
            prefs = context.preferences.addons["blendermcp"].preferences
            host = prefs.host
            port = prefs.port
            
            server = BlenderMCPServer(host=host, port=port)
            server.start()
            is_server_running = True  # 更新状态
            # 注册命令处理器
            register_handlers(server)
            self.report({'INFO'}, f"服务器已启动于 {host}:{port}")
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            self.report({'ERROR'}, f"启动服务器失败: {str(e)}")
            return {'CANCELLED'}

class BLENDERMCP_OT_stop_server(Operator):
    """停止 BlenderMCP 服务器"""
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the BlenderMCP server"
    
    def execute(self, context):
        global server, is_server_running
        try:
            if not is_server_running:
                self.report({'WARNING'}, "服务器未在运行")
                return {'CANCELLED'}
                
            if server:
                server.stop()
                server = None
                is_server_running = False  # 更新状态
                self.report({'INFO'}, "服务器已停止")
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"停止服务器失败: {e}")
            self.report({'ERROR'}, f"停止服务器失败: {str(e)}")
            return {'CANCELLED'} 