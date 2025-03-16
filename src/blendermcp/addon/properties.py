"""
BlenderMCP属性模块

此模块实现了BlenderMCP插件的属性组。
"""

try:
    import bpy
    from bpy.types import PropertyGroup
    from bpy.props import (
        StringProperty,
        BoolProperty,
        CollectionProperty,
        EnumProperty
    )
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    # 在没有bpy模块时创建替代类
    class PropertyGroup:
        """替代Blender的PropertyGroup类，用于服务器独立运行时"""
        def __init__(self):
            pass
    
    # 创建替代属性定义
    def StringProperty(name="", description="", default=""):
        return ""
    
    def BoolProperty(name="", description="", default=True):
        return False
    
    def CollectionProperty(name="", description="", type=None):
        return []
    
    def EnumProperty(name="", description="", items=None, default=None):
        return default if default else (items[0][0] if items and len(items) > 0 else "")

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

def register():
    """注册属性"""
    if HAS_BPY:
        bpy.utils.register_class(BlenderMCPLogEntry)
        bpy.utils.register_class(BlenderMCPProperties)
        
        # 添加到Scene
        bpy.types.Scene.blendermcp = bpy.props.PointerProperty(type=BlenderMCPProperties)

def unregister():
    """注销属性"""
    if HAS_BPY:
        # 删除从Scene
        del bpy.types.Scene.blendermcp
        
        bpy.utils.unregister_class(BlenderMCPProperties)
        bpy.utils.unregister_class(BlenderMCPLogEntry) 