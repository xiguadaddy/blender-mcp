"""
BlenderMCP Properties

This module implements the property groups for the BlenderMCP addon.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    BoolProperty,
    CollectionProperty,
    EnumProperty
)

class BlenderMCPLogEntry(PropertyGroup):
    """Log entry property group"""
    message: StringProperty(
        name="Message",
        description="Log message",
        default=""
    )
    
    level: EnumProperty(
        name="Level",
        description="Log level",
        items=[
            ('DEBUG', "Debug", "Debug message"),
            ('INFO', "Info", "Info message"),
            ('WARNING', "Warning", "Warning message"),
            ('ERROR', "Error", "Error message"),
        ],
        default='INFO'
    )

class BlenderMCPProperties(PropertyGroup):
    """Main property group for BlenderMCP"""
    last_command: StringProperty(
        name="Last Command",
        description="Last executed command",
        default=""
    )
    
    last_result: StringProperty(
        name="Last Result",
        description="Result of the last command",
        default=""
    )
    
    last_result_success: BoolProperty(
        name="Last Result Success",
        description="Whether the last command was successful",
        default=True
    )
    
    logs: CollectionProperty(
        name="Logs",
        description="Command execution logs",
        type=BlenderMCPLogEntry
    )
    
    def add_log(self, message: str, level: str = 'INFO'):
        """Add a log entry"""
        entry = self.logs.add()
        entry.message = message
        entry.level = level
        
    def clear_logs(self):
        """Clear all logs"""
        self.logs.clear()

# 要注册的类
classes = (
    BlenderMCPLogEntry,
    BlenderMCPProperties,
)

def register_properties():
    """注册所有属性类"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 注册主属性组
    bpy.types.Scene.blendermcp = bpy.props.PointerProperty(type=BlenderMCPProperties)

def unregister_properties():
    """注销所有属性类"""
    # 删除主属性组
    del bpy.types.Scene.blendermcp
    
    # 注销类（按照注册的相反顺序）
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 