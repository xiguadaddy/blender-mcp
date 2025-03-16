"""
BlenderMCP工具查看器模块

该模块提供了查看MCP工具列表的功能。
"""

# 尝试导入bpy模块
try:
    import bpy
    from bpy.types import Panel, Operator, UIList, PropertyGroup
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
            
    class UIList:
        """模拟UIList类，用于服务器独立运行时"""
        bl_idname = ""
        
        def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
            pass
    
    class PropertyGroup:
        """模拟PropertyGroup类，用于服务器独立运行时"""
        def __init__(self):
            pass

import os
import sys
import json
import subprocess
import tempfile
from . import server_operators

# 工具列表项
class MCP_UL_ToolsList(UIList):
    """MCP工具列表"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.label(text=item.name, icon='TOOL_SETTINGS')
            
            # 显示工具类别
            if item.category:
                row.label(text=item.category)
            
            # 显示工具状态
            if item.enabled:
                row.label(text="已启用", icon='CHECKMARK')
            else:
                row.label(text="已禁用", icon='X')
        
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=item.name)

# 工具属性
class MCPToolProperty(PropertyGroup if not HAS_BPY else bpy.types.PropertyGroup):
    """MCP工具属性"""
    if HAS_BPY:
        name: bpy.props.StringProperty(name="名称")
        description: bpy.props.StringProperty(name="描述")
        category: bpy.props.StringProperty(name="类别")
        enabled: bpy.props.BoolProperty(name="启用", default=True)
        parameters: bpy.props.StringProperty(name="参数")

# 工具详情面板
class MCP_PT_ToolDetails(Panel):
    """MCP工具详情面板"""
    bl_label = "工具详情"
    bl_idname = "MCP_PT_ToolDetails"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MCP'
    bl_parent_id = "MCP_PT_ToolsPanel"
    
    @classmethod
    def poll(cls, context):
        return (context.scene.mcp_tools and 
                len(context.scene.mcp_tools) > 0 and 
                context.scene.mcp_tool_index >= 0 and 
                context.scene.mcp_tool_index < len(context.scene.mcp_tools))
    
    def draw(self, context):
        layout = self.layout
        tool = context.scene.mcp_tools[context.scene.mcp_tool_index]
        
        # 工具名称
        row = layout.row()
        row.label(text="名称:")
        row.label(text=tool.name)
        
        # 工具描述
        if tool.description:
            box = layout.box()
            box.label(text="描述:")
            box.label(text=tool.description)
        
        # 工具类别
        if tool.category:
            row = layout.row()
            row.label(text="类别:")
            row.label(text=tool.category)
        
        # 工具参数
        if tool.parameters:
            params_box = layout.box()
            params_box.label(text="参数:")
            
            # 尝试解析参数字符串
            try:
                params = json.loads(tool.parameters)
                for param in params:
                    param_row = params_box.row()
                    param_row.label(text=param.get("name", ""))
                    
                    # 参数类型
                    if "type" in param:
                        param_row.label(text=param["type"])
                    
                    # 参数描述
                    if "description" in param:
                        desc_row = params_box.row()
                        desc_row.label(text="  " + param["description"])
            except:
                params_box.label(text="无法解析参数")
        
        # 启用/禁用按钮
        row = layout.row()
        if tool.enabled:
            row.operator("mcp.disable_tool", text="禁用工具", icon='X').tool_name = tool.name
        else:
            row.operator("mcp.enable_tool", text="启用工具", icon='CHECKMARK').tool_name = tool.name

# 工具列表面板
class MCP_PT_ToolsPanel(Panel):
    """MCP工具列表面板"""
    bl_label = "MCP工具列表"
    bl_idname = "MCP_PT_ToolsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MCP'
    
    def draw(self, context):
        layout = self.layout
        
        # 刷新工具列表按钮
        row = layout.row()
        row.operator("mcp.refresh_tools_list", text="刷新工具列表", icon='FILE_REFRESH')
        
        # 工具列表
        row = layout.row()
        row.template_list("MCP_UL_ToolsList", "", context.scene, "mcp_tools", context.scene, "mcp_tool_index")
        
        # 工具列表操作按钮
        col = row.column(align=True)
        col.operator("mcp.enable_all_tools", icon='CHECKMARK', text="")
        col.operator("mcp.disable_all_tools", icon='X', text="")
        
        # 导出工具列表按钮
        row = layout.row()
        row.operator("mcp.export_tools_list", text="导出工具列表", icon='EXPORT')

# 刷新工具列表操作
class MCP_OT_RefreshToolsList(Operator):
    """刷新MCP工具列表"""
    bl_idname = "mcp.refresh_tools_list"
    bl_label = "刷新工具列表"
    bl_description = "从MCP服务器获取最新的工具列表"
    
    def execute(self, context):
        # 检查服务器是否运行
        if not server_operators.is_server_running():
            self.report({'ERROR'}, "MCP服务器未运行")
            return {'CANCELLED'}
        
        # 刷新工具列表
        if server_operators.refresh_tools_list():
            # 获取工具列表
            tools = server_operators.get_available_tools()
            
            # 清空当前工具列表
            context.scene.mcp_tools.clear()
            
            # 添加工具到列表
            for tool_data in tools:
                tool = context.scene.mcp_tools.add()
                tool.name = tool_data.get("name", "未命名工具")
                tool.description = tool_data.get("description", "")
                
                # 从工具名称中提取类别
                name_parts = tool.name.split(".")
                if len(name_parts) > 1:
                    tool.category = name_parts[0]
                
                # 保存参数
                if "parameters" in tool_data:
                    import json
                    tool.parameters = json.dumps(tool_data["parameters"])
                
                # 默认启用
                tool.enabled = True
            
            self.report({'INFO'}, f"已刷新工具列表，共 {len(tools)} 个工具")
        else:
            self.report({'ERROR'}, "刷新工具列表失败")
        
        return {'FINISHED'}

# 启用工具操作
class MCP_OT_EnableTool(Operator):
    """启用MCP工具"""
    bl_idname = "mcp.enable_tool"
    bl_label = "启用工具"
    bl_description = "启用选定的MCP工具"
    
    tool_name: bpy.props.StringProperty(name="工具名称")
    
    def execute(self, context):
        # 查找工具
        for tool in context.scene.mcp_tools:
            if tool.name == self.tool_name:
                tool.enabled = True
                self.report({'INFO'}, f"已启用工具: {self.tool_name}")
                break
        
        return {'FINISHED'}

# 禁用工具操作
class MCP_OT_DisableTool(Operator):
    """禁用MCP工具"""
    bl_idname = "mcp.disable_tool"
    bl_label = "禁用工具"
    bl_description = "禁用选定的MCP工具"
    
    tool_name: bpy.props.StringProperty(name="工具名称")
    
    def execute(self, context):
        # 查找工具
        for tool in context.scene.mcp_tools:
            if tool.name == self.tool_name:
                tool.enabled = False
                self.report({'INFO'}, f"已禁用工具: {self.tool_name}")
                break
        
        return {'FINISHED'}

# 启用所有工具操作
class MCP_OT_EnableAllTools(Operator):
    """启用所有MCP工具"""
    bl_idname = "mcp.enable_all_tools"
    bl_label = "启用所有工具"
    bl_description = "启用所有MCP工具"
    
    def execute(self, context):
        for tool in context.scene.mcp_tools:
            tool.enabled = True
        
        self.report({'INFO'}, "已启用所有工具")
        return {'FINISHED'}

# 禁用所有工具操作
class MCP_OT_DisableAllTools(Operator):
    """禁用所有MCP工具"""
    bl_idname = "mcp.disable_all_tools"
    bl_label = "禁用所有工具"
    bl_description = "禁用所有MCP工具"
    
    def execute(self, context):
        for tool in context.scene.mcp_tools:
            tool.enabled = False
        
        self.report({'INFO'}, "已禁用所有工具")
        return {'FINISHED'}

# 导出工具列表操作
class MCP_OT_ExportToolsList(Operator):
    """导出MCP工具列表"""
    bl_idname = "mcp.export_tools_list"
    bl_label = "导出工具列表"
    bl_description = "将MCP工具列表导出到文件"
    
    def execute(self, context):
        if not context.scene.mcp_tools:
            self.report({'ERROR'}, "工具列表为空")
            return {'CANCELLED'}
        
        # 创建导出文件
        export_file = os.path.join(tempfile.gettempdir(), "mcp_tools_list.md")
        
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write("# MCP工具列表\n\n")
                
                # 按类别分组
                categories = {}
                for tool in context.scene.mcp_tools:
                    category = tool.category if tool.category else "其他"
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(tool)
                
                # 写入工具信息
                for category, tools in sorted(categories.items()):
                    f.write(f"## {category}\n\n")
                    
                    for tool in tools:
                        # 工具名称和状态
                        status = "✅ 已启用" if tool.enabled else "❌ 已禁用"
                        f.write(f"### {tool.name} ({status})\n\n")
                        
                        # 工具描述
                        if tool.description:
                            f.write(f"**描述**: {tool.description}\n\n")
                        
                        # 工具参数
                        if tool.parameters:
                            f.write("**参数**:\n\n")
                            
                            import json
                            try:
                                params = json.loads(tool.parameters)
                                for param in params:
                                    param_name = param.get("name", "未命名")
                                    param_type = param.get("type", "未知类型")
                                    param_desc = param.get("description", "无描述")
                                    
                                    f.write(f"- `{param_name}` ({param_type}): {param_desc}\n")
                            except:
                                f.write("无法解析参数\n")
                            
                            f.write("\n")
            
            # 在文本编辑器中打开
            text = bpy.data.texts.load(export_file)
            
            # 切换到文本编辑器区域
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'TEXT_EDITOR':
                        area.spaces[0].text = text
                        self.report({'INFO'}, "工具列表已导出并在文本编辑器中打开")
                        return {'FINISHED'}
            
            # 如果没有找到文本编辑器区域，尝试使用外部编辑器
            if sys.platform == 'win32':
                os.startfile(export_file)
            elif sys.platform == 'darwin':
                subprocess.call(['open', export_file])
            else:
                subprocess.call(['xdg-open', export_file])
            
            self.report({'INFO'}, f"工具列表已导出到: {export_file}")
        except Exception as e:
            self.report({'ERROR'}, f"导出工具列表失败: {str(e)}")
        
        return {'FINISHED'}

# 注册和注销
classes = (
    MCPToolProperty,
    MCP_UL_ToolsList,
    MCP_PT_ToolsPanel,
    MCP_PT_ToolDetails,
    MCP_OT_RefreshToolsList,
    MCP_OT_EnableTool,
    MCP_OT_DisableTool,
    MCP_OT_EnableAllTools,
    MCP_OT_DisableAllTools,
    MCP_OT_ExportToolsList,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 注册属性
    bpy.types.Scene.mcp_tools = bpy.props.CollectionProperty(type=MCPToolProperty)
    bpy.types.Scene.mcp_tool_index = bpy.props.IntProperty(default=0)

def unregister():
    # 注销属性
    del bpy.types.Scene.mcp_tool_index
    del bpy.types.Scene.mcp_tools
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 