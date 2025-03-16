"""
BlenderMCP首选项模块

该模块定义了BlenderMCP插件的首选项设置。
"""

import os

# 尝试导入bpy模块
try:
    import bpy
    from bpy.types import AddonPreferences
    from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    # 创建模拟类
    class AddonPreferences:
        """模拟AddonPreferences类"""
        pass

# 只在bpy可用时定义首选项类
if HAS_BPY:
    class MCPAddonPreferences(AddonPreferences):
        """MCP插件首选项"""
        bl_idname = "blendermcp"
        
        # 服务器模式
        server_mode: EnumProperty(
            name="服务器模式",
            description="选择MCP服务器的运行模式",
            items=[
                ('WEBSOCKET', "WebSocket", "使用WebSocket协议运行服务器，允许远程连接"),
                ('STDIO', "标准输入/输出", "使用标准输入/输出运行服务器，适用于本地进程通信")
            ],
            default='WEBSOCKET'
        )
        
        # WebSocket设置
        websocket_host: StringProperty(
            name="主机",
            description="WebSocket服务器主机地址",
            default="localhost"
        )
        
        websocket_port: IntProperty(
            name="端口",
            description="WebSocket服务器端口",
            default=9876,
            min=1024,
            max=65535
        )
        
        # 自动启动设置
        auto_start_server: BoolProperty(
            name="启动Blender时自动启动服务器",
            description="在Blender启动时自动启动MCP服务器",
            default=False
        )
        
        # 日志设置
        log_level: EnumProperty(
            name="日志级别",
            description="设置日志记录的详细程度",
            items=[
                ('DEBUG', "调试", "记录所有详细信息，包括调试信息"),
                ('INFO', "信息", "记录一般信息和错误"),
                ('WARNING', "警告", "仅记录警告和错误"),
                ('ERROR', "错误", "仅记录错误")
            ],
            default='INFO'
        )
        
        # 性能设置
        max_connections: IntProperty(
            name="最大连接数",
            description="WebSocket服务器允许的最大并发连接数",
            default=5,
            min=1,
            max=50
        )
        
        connection_timeout: IntProperty(
            name="连接超时(秒)",
            description="WebSocket连接的超时时间(秒)",
            default=60,
            min=10,
            max=300
        )
        
        # 安全设置
        enable_authentication: BoolProperty(
            name="启用身份验证",
            description="要求客户端提供API密钥进行身份验证",
            default=False
        )
        
        api_key: StringProperty(
            name="API密钥",
            description="用于身份验证的API密钥",
            default="",
            subtype='PASSWORD'
        )
        
        # 工具设置
        enable_all_tools: BoolProperty(
            name="启用所有工具",
            description="启用所有可用的MCP工具",
            default=True
        )
        
        # 界面设置
        show_advanced_options: BoolProperty(
            name="显示高级选项",
            description="在界面中显示高级配置选项",
            default=False
        )
        
        def draw(self, context):
            layout = self.layout
            
            # 基本设置
            box = layout.box()
            box.label(text="基本设置", icon='SETTINGS')
            
            # 服务器模式
            row = box.row()
            row.label(text="服务器模式:")
            row.prop(self, "server_mode", text="")
            
            # WebSocket设置
            if self.server_mode == 'WEBSOCKET':
                websocket_box = box.box()
                websocket_box.label(text="WebSocket设置")
                
                row = websocket_box.row()
                row.label(text="主机:")
                row.prop(self, "websocket_host", text="")
                
                row = websocket_box.row()
                row.label(text="端口:")
                row.prop(self, "websocket_port", text="")
            
            # 自动启动
            row = box.row()
            row.prop(self, "auto_start_server")
            
            # 日志设置
            row = box.row()
            row.label(text="日志级别:")
            row.prop(self, "log_level", text="")
            
            # 高级设置
            row = layout.row()
            row.prop(self, "show_advanced_options", toggle=True)
            
            if self.show_advanced_options:
                # 性能设置
                perf_box = layout.box()
                perf_box.label(text="性能设置", icon='PREFERENCES')
                
                row = perf_box.row()
                row.label(text="最大连接数:")
                row.prop(self, "max_connections", text="")
                
                row = perf_box.row()
                row.label(text="连接超时(秒):")
                row.prop(self, "connection_timeout", text="")
                
                # 安全设置
                security_box = layout.box()
                security_box.label(text="安全设置", icon='LOCKED')
                
                row = security_box.row()
                row.prop(self, "enable_authentication")
                
                if self.enable_authentication:
                    row = security_box.row()
                    row.label(text="API密钥:")
                    row.prop(self, "api_key", text="")
                
                # 工具设置
                tools_box = layout.box()
                tools_box.label(text="工具设置", icon='TOOL_SETTINGS')
                
                row = tools_box.row()
                row.prop(self, "enable_all_tools")

    def get_addon_preferences(context):
        """获取插件首选项"""
        return context.preferences.addons["blendermcp"].preferences
    
    # 注册和注销
    def register():
        """注册首选项"""
        if HAS_BPY:
            bpy.utils.register_class(MCPAddonPreferences)

    def unregister():
        """注销首选项"""
        if HAS_BPY:
            bpy.utils.unregister_class(MCPAddonPreferences)
else:
    # 在没有bpy时提供模拟实现
    class MCPAddonPreferences:
        """模拟MCP插件首选项"""
        server_mode = 'WEBSOCKET'
        websocket_host = 'localhost'
        websocket_port = 9876
        auto_start_server = False
        log_level = 'INFO'
        max_connections = 5
        connection_timeout = 60
        enable_authentication = False
        api_key = ''
        enable_all_tools = True
        show_advanced_options = False
    
    def get_addon_preferences(context=None):
        """获取模拟的插件首选项"""
        return MCPAddonPreferences()
    
    def register():
        """模拟注册函数"""
        pass
    
    def unregister():
        """模拟注销函数"""
        pass 