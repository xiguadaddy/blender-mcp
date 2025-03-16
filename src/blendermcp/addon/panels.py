"""
BlenderMCP面板模块

该模块定义了BlenderMCP插件的用户界面面板。
"""

# 尝试导入bpy模块
try:
    import bpy
    from bpy.types import Panel, Operator
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    # 创建一个模拟的Panel类和Operator类
    class Panel:
        """模拟Panel类，用于服务器独立运行时"""
        bl_idname = ""
        bl_label = ""
        bl_category = ""
        bl_space_type = ""
        bl_region_type = ""
        
        def poll(cls, context):
            return True
        
        def draw(self, context):
            pass
    
    class Operator:
        """模拟Operator类，用于服务器独立运行时"""
        bl_idname = ""
        bl_label = ""
        bl_description = ""
        
        def execute(self, context):
            return {'FINISHED'}

import os
import sys
import tempfile
import time
import json
from pathlib import Path
from . import preferences
from . import server_operators
from . import tool_viewer

# 只在bpy可用时定义面板类
if HAS_BPY:
    class MCP_PT_Panel(Panel):
        """MCP面板"""
        bl_label = "MCP"
        bl_idname = "MCP_PT_Panel"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = 'MCP'

        def draw(self, context):
            layout = self.layout
            
            # 获取服务器状态
            is_running = server_operators.is_server_running()
            
            # 状态显示
            status_box = layout.box()
            status_box.label(text="MCP服务器状态")
            
            if is_running:
                status_box.label(text="状态: 运行中", icon='CHECKMARK')
                
                # 停止服务器按钮
                status_box.operator("blendermcp.stop_server", icon='PAUSE')
            else:
                status_box.label(text="状态: 已停止", icon='X')
                
                # 启动服务器按钮
                status_box.operator("blendermcp.start_server", icon='PLAY')
            
            # 日志操作
            log_box = layout.box()
            log_box.label(text="服务器日志")
            log_row = log_box.row()
            log_row.operator("blendermcp.view_server_log", icon='TEXT')
            log_row.operator("blendermcp.copy_server_log", icon='COPYDOWN')
            
            # 服务器详细信息
            if is_running:
                # 服务器模式
                mode_row = status_box.row()
                mode_row.label(text="模式:")
                mode_row.label(text=server_operators.get_server_mode().upper())
                
                # 服务器地址
                if server_operators.get_server_mode() == "websocket":
                    url_row = status_box.row()
                    url_row.label(text="WebSocket URL:")
                    url_row.label(text=f"ws://{server_operators.get_server_host()}:{server_operators.get_server_port()}")
                
                # 运行时间
                if "uptime" in server_operators.get_server_status():
                    uptime_row = status_box.row()
                    uptime_row.label(text="运行时间:")
                    uptime_row.label(text=server_operators.get_server_status()["uptime"])
                
                # 连接数
                if "connections" in server_operators.get_server_status():
                    conn_row = status_box.row()
                    conn_row.label(text="活动连接:")
                    conn_row.label(text=str(server_operators.get_server_status()["connections"]))
                
                # 请求数
                if "requests" in server_operators.get_server_status():
                    req_row = status_box.row()
                    req_row.label(text="处理请求:")
                    req_row.label(text=str(server_operators.get_server_status()["requests"]))
                
                # 进程ID
                if "pid" in server_operators.get_server_status():
                    pid_row = status_box.row()
                    pid_row.label(text="进程ID:")
                    pid_row.label(text=str(server_operators.get_server_status()["pid"]))
            
            # 服务器控制按钮
            control_box = layout.box()
            control_box.label(text="服务器控制")
            
            row = control_box.row()
            if not is_running:
                row.operator("blendermcp.start_server", text="启动服务器", icon='PLAY')
            else:
                row.operator("blendermcp.stop_server", text="停止服务器", icon='PAUSE')
            
            # WebSocket URL复制按钮
            if is_running and server_operators.get_server_mode() == "websocket":
                url_row = control_box.row()
                url_row.operator("blendermcp.copy_websocket_url", text="复制WebSocket URL", icon='COPYDOWN')
            
            # 服务器配置
            config_box = layout.box()
            config_box.label(text="服务器配置")
            
            # 获取插件首选项
            addon_prefs = preferences.get_addon_preferences(context)
            
            # 服务器模式选择
            mode_row = config_box.row()
            mode_row.label(text="模式:")
            mode_row.prop(addon_prefs, "server_mode", text="")
            
            # WebSocket模式配置
            if addon_prefs.server_mode == 'WEBSOCKET':
                host_row = config_box.row()
                host_row.label(text="主机:")
                host_row.prop(addon_prefs, "websocket_host", text="")
                
                port_row = config_box.row()
                port_row.label(text="端口:")
                port_row.prop(addon_prefs, "websocket_port", text="")
            
            # 自动启动选项
            auto_row = config_box.row()
            auto_row.prop(addon_prefs, "auto_start_server")
            
            # 日志查看器
            log_box = layout.box()
            log_box.label(text="日志")
            
            # 日志文件路径
            log_path = os.path.join(tempfile.gettempdir(), "blendermcp_addon.log")
            if os.path.exists(log_path):
                log_row = log_box.row()
                log_row.operator("blendermcp.view_server_log", text="查看日志文件", icon='TEXT')
            
            # 工具管理 - 确保使用存在的操作符，如果新版不支持这些功能，则不显示
            if hasattr(bpy.ops, "blendermcp") and hasattr(bpy.ops.blendermcp, "start_server"):
                tools_box = layout.box()
                tools_box.label(text="插件状态")
                
                # 版本信息
                version_row = tools_box.row()
                version_row.label(text="版本: 0.3.0")
                
                # 添加帮助链接
                help_row = tools_box.row()
                help_row.operator("wm.url_open", text="使用帮助").url = "https://github.com/yourusername/blender-mcp/blob/main/README.md"


# 注册和注销
def register():
    """注册面板"""
    if HAS_BPY:
        bpy.utils.register_class(MCP_PT_Panel)

def unregister():
    """注销面板"""
    if HAS_BPY:
        bpy.utils.unregister_class(MCP_PT_Panel) 