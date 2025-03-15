"""
BlenderMCP Client Tools

This module defines all available tools and their registration.
"""

from typing import Dict, Any, List
from .config import ToolDefinition, MCPConfig

class ToolRegistry:
    """工具注册器"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self._register_all_tools()
        
    def _register_all_tools(self):
        """注册所有可用工具"""
        # 材质工具
        self._register_material_tools()
        # 灯光工具
        self._register_lighting_tools()
        # 渲染工具
        self._register_render_tools()
        # 建模工具
        self._register_modeling_tools()
        # 动画工具
        self._register_animation_tools()
        
    def _register_material_tools(self):
        """注册材质相关工具"""
        # 基础材质
        self.config.register_tool(ToolDefinition(
            name="set_material",
            description="设置对象的基础材质属性",
            category="material",
            parameters={
                "object_name": {"type": "string", "description": "目标对象名称"},
                "material_name": {"type": "string", "description": "材质名称", "optional": True},
                "color": {"type": "array", "description": "RGBA颜色值", "optional": True},
                "metallic": {"type": "float", "description": "金属度", "optional": True},
                "roughness": {"type": "float", "description": "粗糙度", "optional": True},
                "specular": {"type": "float", "description": "镜面反射强度", "optional": True}
            }
        ))
        
        # 节点材质
        self.config.register_tool(ToolDefinition(
            name="create_node_material",
            description="创建节点基础的高级材质",
            category="material",
            parameters={
                "name": {"type": "string", "description": "材质名称"},
                "node_setup": {
                    "type": "object",
                    "description": "节点设置",
                    "properties": {
                        "nodes": {"type": "object", "description": "节点定义"},
                        "links": {"type": "array", "description": "节点连接"}
                    }
                }
            }
        ))
        
    def _register_lighting_tools(self):
        """注册灯光相关工具"""
        # 创建灯光
        self.config.register_tool(ToolDefinition(
            name="create_light",
            description="创建各种类型的灯光",
            category="lighting",
            parameters={
                "type": {"type": "string", "description": "灯光类型 (POINT, SUN, SPOT, AREA)"},
                "name": {"type": "string", "description": "灯光名称", "optional": True},
                "location": {"type": "array", "description": "位置坐标", "optional": True},
                "energy": {"type": "float", "description": "光照强度", "optional": True},
                "color": {"type": "array", "description": "灯光颜色", "optional": True},
                "shadow": {"type": "boolean", "description": "是否产生阴影", "optional": True}
            }
        ))
        
        # 环境光遮蔽
        self.config.register_tool(ToolDefinition(
            name="set_ambient_occlusion",
            description="设置环境光遮蔽",
            category="lighting",
            parameters={
                "factor": {"type": "float", "description": "AO强度"},
                "distance": {"type": "float", "description": "AO距离"}
            }
        ))
        
    def _register_render_tools(self):
        """注册渲染相关工具"""
        # 渲染设置
        self.config.register_tool(ToolDefinition(
            name="set_render_settings",
            description="配置渲染设置",
            category="render",
            parameters={
                "engine": {"type": "string", "description": "渲染引擎 (CYCLES, EEVEE)"},
                "samples": {"type": "integer", "description": "采样数量"},
                "resolution_x": {"type": "integer", "description": "渲染宽度"},
                "resolution_y": {"type": "integer", "description": "渲染高度"},
                "use_gpu": {"type": "boolean", "description": "是否使用GPU渲染"}
            }
        ))
        
        # 渲染图像
        self.config.register_tool(ToolDefinition(
            name="render_image",
            description="渲染当前场景",
            category="render",
            parameters={
                "output_path": {"type": "string", "description": "输出文件路径"},
                "format": {"type": "string", "description": "输出格式 (PNG, JPEG, etc.)"},
                "quality": {"type": "integer", "description": "输出质量"}
            }
        ))
        
    def _register_modeling_tools(self):
        """注册建模相关工具"""
        # 网格编辑
        self.config.register_tool(ToolDefinition(
            name="edit_mesh",
            description="编辑网格几何体",
            category="modeling",
            parameters={
                "object_name": {"type": "string", "description": "目标对象名称"},
                "operation": {"type": "string", "description": "操作类型"},
                "parameters": {"type": "object", "description": "操作参数"}
            }
        ))
        
        # 修改器
        self.config.register_tool(ToolDefinition(
            name="add_modifier",
            description="添加对象修改器",
            category="modeling",
            parameters={
                "object_name": {"type": "string", "description": "目标对象名称"},
                "modifier_type": {"type": "string", "description": "修改器类型"},
                "parameters": {"type": "object", "description": "修改器参数"}
            }
        ))
        
    def _register_animation_tools(self):
        """注册动画相关工具"""
        # 关键帧动画
        self.config.register_tool(ToolDefinition(
            name="create_animation",
            description="创建关键帧动画",
            category="animation",
            parameters={
                "object_name": {"type": "string", "description": "目标对象名称"},
                "property_path": {"type": "string", "description": "动画属性路径"},
                "keyframes": {"type": "object", "description": "关键帧数据"}
            }
        ))
        
        # 物理模拟
        self.config.register_tool(ToolDefinition(
            name="setup_physics",
            description="设置物理模拟",
            category="animation",
            parameters={
                "object_name": {"type": "string", "description": "目标对象名称"},
                "physics_type": {"type": "string", "description": "物理类型"},
                "parameters": {"type": "object", "description": "物理参数"}
            }
        )) 