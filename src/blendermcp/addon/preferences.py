"""
BlenderMCP addon preferences
"""

import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty

class BlenderMCPAddonPreferences(AddonPreferences):
    bl_idname = __package__.split('.')[0]
    
    host: StringProperty(
        name="主机",
        description="服务器主机地址",
        default="localhost"
    )
    
    port: IntProperty(
        name="端口",
        description="服务器端口",
        default=9876,
        min=1024,
        max=65535
    )
    
    auto_start: BoolProperty(
        name="自动启动",
        description="启用插件时自动启动服务器",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        
        # 服务器状态显示
        box = layout.box()
        row = box.row()
        
        # 从server_operators模块获取状态
        from . import server_operators
        if server_operators.is_server_running:
            row.label(text=f"服务器状态: 运行中 ({self.host}:{self.port})", icon='CHECKMARK')
        else:
            row.label(text="服务器状态: 已停止", icon='X')
        
        # 服务器设置
        box = layout.box()
        box.label(text="服务器设置:")
        box.prop(self, "host")
        box.prop(self, "port")
        box.prop(self, "auto_start")
        
        # 服务器控制按钮
        row = layout.row()
        row.scale_y = 1.5
        if server_operators.is_server_running:
            row.operator("blendermcp.stop_server", text="停止服务器", icon='PAUSE')
        else:
            row.operator("blendermcp.start_server", text="启动服务器", icon='PLAY') 