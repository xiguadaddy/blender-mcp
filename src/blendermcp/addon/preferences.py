"""
BlenderMCP首选项模块

该模块定义了BlenderMCP插件的首选项设置。
"""

import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty

class BlenderMCPPreferences(AddonPreferences):
    """BlenderMCP插件首选项"""
    bl_idname = "blendermcp"
    
    # 服务器模式
    server_mode: EnumProperty(
        name="服务器模式",
        description="MCP服务器的运行模式",
        items=[
            ('websocket', "WebSocket", "使用WebSocket协议运行服务器"),
            ('stdio', "标准输入/输出", "使用标准输入/输出运行服务器")
        ],
        default='websocket'
    )
    
    # WebSocket设置
    server_host: StringProperty(
        name="主机",
        description="WebSocket服务器主机名",
        default="localhost"
    )
    
    server_port: IntProperty(
        name="端口",
        description="WebSocket服务器端口",
        default=9876,
        min=1024,
        max=65535
    )
    
    # 自动启动设置
    auto_start: BoolProperty(
        name="自动启动",
        description="插件加载时自动启动MCP服务器",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        
        # 服务器状态显示
        box = layout.box()
        row = box.row()
        
        # 从server_operators模块获取状态
        from .server_operators import is_mcp_server_running, get_mcp_server_url
        if is_mcp_server_running():
            row.label(text="MCP服务器状态: 运行中", icon='CHECKMARK')
            if self.server_mode == 'websocket':
                url = get_mcp_server_url()
                row = box.row()
                row.label(text=f"WebSocket URL: {url}")
                row = box.row()
                row.operator("blendermcp.copy_mcp_websocket_url", text="复制URL", icon='COPYDOWN')
        else:
            row.label(text="MCP服务器状态: 已停止", icon='X')
        
        # MCP服务器设置
        box = layout.box()
        box.label(text="MCP服务器设置")
        
        # 服务器模式
        row = box.row()
        row.prop(self, "server_mode")
        
        # WebSocket设置
        if self.server_mode.lower() == "websocket":
            row = box.row()
            row.prop(self, "server_host")
            
            row = box.row()
            row.prop(self, "server_port")
        
        # 自动启动设置
        row = box.row()
        row.prop(self, "auto_start")
        
        # 服务器控制按钮
        row = layout.row()
        row.scale_y = 1.5
        if is_mcp_server_running():
            row.operator("blendermcp.stop_mcp_server", text="停止MCP服务器", icon='PAUSE')
        else:
            row.operator("blendermcp.start_mcp_server", text="启动MCP服务器", icon='PLAY')

def register():
    bpy.utils.register_class(BlenderMCPPreferences)

def unregister():
    bpy.utils.unregister_class(BlenderMCPPreferences) 