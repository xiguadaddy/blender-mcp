"""
BlenderMCP UI Panels

This module implements the UI panels for the BlenderMCP addon.
"""

import bpy
from bpy.types import Panel

class VIEW3D_PT_blendermcp_operations(Panel):
    """Operations panel for BlenderMCP"""
    bl_label = "Operations"
    bl_idname = "VIEW3D_PT_blendermcp_operations"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        """Draw the panel"""
        layout = self.layout
        
        # 服务器控制按钮
        box = layout.box()
        box.label(text="Server Control:")
        row = box.row()
        row.operator("blendermcp.start_server", text="Start Server")
        row.operator("blendermcp.stop_server", text="Stop Server")
        
        # 命令执行状态
        box = layout.box()
        box.label(text="Last Command:")
        row = box.row()
        row.label(text=context.scene.blendermcp.last_command or "None")
        
        # 命令结果
        box = layout.box()
        box.label(text="Result:")
        row = box.row()
        if context.scene.blendermcp.last_result_success:
            row.label(text="Success", icon='CHECKMARK')
        else:
            row.label(text="Failed", icon='ERROR')
        row = box.row()
        row.label(text=context.scene.blendermcp.last_result or "No result")

class VIEW3D_PT_blendermcp_log(Panel):
    """Log panel for BlenderMCP"""
    bl_label = "Log"
    bl_idname = "VIEW3D_PT_blendermcp_log"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        """Draw the panel"""
        layout = self.layout
        
        # 日志显示
        box = layout.box()
        for log in context.scene.blendermcp.logs:
            row = box.row()
            if log.level == 'INFO':
                icon = 'INFO'
            elif log.level == 'WARNING':
                icon = 'ERROR'
            elif log.level == 'ERROR':
                icon = 'CANCEL'
            else:
                icon = 'NONE'
            row.label(text=log.message, icon=icon)
        
        # 清除日志按钮
        row = layout.row()
        row.operator("blendermcp.clear_log", text="Clear Log")

# 要注册的类
classes = (
    VIEW3D_PT_blendermcp_operations,
    VIEW3D_PT_blendermcp_log,
)

def register_panels():
    """注册所有面板类"""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_panels():
    """注销所有面板类"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 