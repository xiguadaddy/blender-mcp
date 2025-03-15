"""
BlenderMCP Operators

This module implements the operators for the BlenderMCP addon.
"""

import bpy
from bpy.types import Operator

class BLENDERMCP_OT_clear_log(Operator):
    """Clear the command log"""
    bl_idname = "blendermcp.clear_log"
    bl_label = "Clear Log"
    bl_description = "Clear the command execution log"
    
    def execute(self, context):
        context.scene.blendermcp.clear_logs()
        return {'FINISHED'}

class BLENDERMCP_OT_execute_command(Operator):
    """Execute a BlenderMCP command"""
    bl_idname = "blendermcp.execute_command"
    bl_label = "Execute Command"
    bl_description = "Execute a BlenderMCP command"
    
    command: bpy.props.StringProperty(
        name="Command",
        description="Command to execute",
        default=""
    )
    
    params: bpy.props.StringProperty(
        name="Parameters",
        description="Command parameters in JSON format",
        default="{}"
    )
    
    def execute(self, context):
        from .. import _server_instance
        import json
        import asyncio
        
        if not _server_instance:
            self.report({'ERROR'}, "Server is not running")
            return {'CANCELLED'}
            
        try:
            # 解析参数
            params = json.loads(self.params)
            
            # 更新状态
            context.scene.blendermcp.last_command = self.command
            
            # 执行命令
            handler = _server_instance.command_registry.get_handler(self.command)
            if not handler:
                raise ValueError(f"Unknown command: {self.command}")
                
            # 在事件循环中执行命令
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(handler(params))
            
            # 更新结果
            context.scene.blendermcp.last_result = json.dumps(result)
            context.scene.blendermcp.last_result_success = True
            context.scene.blendermcp.add_log(
                f"Command '{self.command}' executed successfully",
                'INFO'
            )
            
            return {'FINISHED'}
            
        except Exception as e:
            # 更新错误状态
            context.scene.blendermcp.last_result = str(e)
            context.scene.blendermcp.last_result_success = False
            context.scene.blendermcp.add_log(
                f"Error executing command '{self.command}': {str(e)}",
                'ERROR'
            )
            
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

# 要注册的类
classes = (
    BLENDERMCP_OT_clear_log,
    BLENDERMCP_OT_execute_command,
)

def register_operators():
    """注册所有操作符类"""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_operators():
    """注销所有操作符类"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 