"""
BlenderMCP面板模块

该模块提供了BlenderMCP的用户界面面板。
"""

import bpy
from . import server_operators

class MCP_PT_Panel(bpy.types.Panel):
    """MCP主面板"""
    bl_label = "MCP服务器"
    bl_idname = "MCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MCP'
    
    def draw(self, context):
        layout = self.layout
        preferences = context.preferences.addons["blendermcp"].preferences
        
        # 服务器状态
        box = layout.box()
        row = box.row()
        
        if server_operators.is_server_running():
            row.label(text="状态: 运行中", icon='CHECKMARK')
            
            # 显示服务器模式
            mode = preferences.server_mode.lower()
            if mode == "websocket":
                row = box.row()
                row.label(text=f"模式: WebSocket")
                
                # 显示WebSocket URL
                url = server_operators.get_server_url()
                if url:
                    row = box.row()
                    row.label(text=f"URL: {url}")
                    
                    # 复制URL按钮
                    row = box.row()
                    row.operator("mcp.copy_websocket_url", text="复制URL", icon='COPYDOWN')
            else:
                row = box.row()
                row.label(text=f"模式: 标准输入/输出")
            
            # 停止服务器按钮
            row = box.row()
            row.operator("mcp.stop_server", text="停止服务器", icon='PAUSE')
        else:
            row.label(text="状态: 已停止", icon='X')
            
            # 启动服务器按钮
            row = box.row()
            row.operator("mcp.start_server", text="启动服务器", icon='PLAY')
        
        # 服务器设置
        box = layout.box()
        box.label(text="服务器设置:")
        
        # 服务器模式
        row = box.row()
        row.prop(preferences, "server_mode", text="模式")
        
        # WebSocket设置
        if preferences.server_mode.lower() == "websocket":
            row = box.row()
            row.prop(preferences, "server_host", text="主机")
            
            row = box.row()
            row.prop(preferences, "server_port", text="端口")
        
        # 自动启动设置
        row = box.row()
        row.prop(preferences, "auto_start", text="自动启动")

def register():
    bpy.utils.register_class(MCP_PT_Panel)

def unregister():
    bpy.utils.unregister_class(MCP_PT_Panel) 