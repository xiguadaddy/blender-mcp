"""
BlenderMCP Client Tools

This module defines all available tools and their registration.
"""

from typing import Dict, Any, List
from .config import ToolDefinition, MCPConfig
from dataclasses import dataclass, field
from typing import Optional, Callable
import json
import jsonschema
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolDefinition:
    """MCP工具定义类"""
    name: str
    description: str
    category: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None
    is_error: bool = False
    version: str = "1.0"
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_schema": self.input_schema,
            "version": self.version,
            "examples": self.examples
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数是否符合schema"""
        try:
            jsonschema.validate(instance=params, schema=self.input_schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"参数验证失败: {e}")
            return False

class ToolRegistry:
    """MCP工具注册表"""
    def __init__(self, config: MCPConfig):
        """初始化工具注册表
        
        Args:
            config: MCP配置实例
        """
        self.config = config
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        self._observers: List[Callable] = []
        self._register_all_tools()

    def register_tool(self, tool: ToolDefinition) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)
        self._notify_observers()

    def unregister_tool(self, tool_name: str) -> None:
        """注销工具"""
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            del self._tools[tool_name]
            self._categories[tool.category].remove(tool_name)
            self._notify_observers()

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(tool_name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        """列出工具"""
        if category:
            tool_names = self._categories.get(category, [])
            return [self._tools[name] for name in tool_names]
        return list(self._tools.values())

    def add_observer(self, observer: Callable) -> None:
        """添加观察者"""
        self._observers.append(observer)

    def _notify_observers(self) -> None:
        """通知所有观察者工具列表已更改"""
        for observer in self._observers:
            observer()

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
        self.register_tool(ToolDefinition(
            name="set_material",
            description="设置对象的基础材质属性",
            category="material",
            input_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "目标对象名称"},
                    "material_name": {"type": "string", "description": "材质名称"},
                    "color": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                        "description": "RGBA颜色值"
                    },
                    "metallic": {"type": "number", "description": "金属度"},
                    "roughness": {"type": "number", "description": "粗糙度"},
                    "specular": {"type": "number", "description": "镜面反射强度"}
                },
                "required": ["object_name"]
            }
        ))
        
        # 节点材质
        self.register_tool(ToolDefinition(
            name="create_node_material",
            description="创建节点基础的高级材质",
            category="material",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "材质名称"},
                    "node_setup": {
                        "type": "object",
                        "properties": {
                            "nodes": {"type": "object", "description": "节点定义"},
                            "links": {"type": "array", "description": "节点连接"}
                        },
                        "required": ["nodes", "links"]
                    }
                },
                "required": ["name", "node_setup"]
            }
        ))
        
    def _register_lighting_tools(self):
        """注册灯光相关工具"""
        # 创建灯光
        self.register_tool(ToolDefinition(
            name="create_light",
            description="创建各种类型的灯光",
            category="lighting",
            input_schema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["POINT", "SUN", "SPOT", "AREA"],
                        "description": "灯光类型"
                    },
                    "name": {"type": "string", "description": "灯光名称"},
                    "location": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "位置坐标"
                    },
                    "energy": {"type": "number", "description": "光照强度"},
                    "color": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "灯光颜色"
                    },
                    "shadow": {"type": "boolean", "description": "是否产生阴影"}
                },
                "required": ["type"]
            }
        ))
        
        # 环境光遮蔽
        self.register_tool(ToolDefinition(
            name="set_ambient_occlusion",
            description="设置环境光遮蔽",
            category="lighting",
            input_schema={
                "type": "object",
                "properties": {
                    "factor": {"type": "number", "description": "AO强度"},
                    "distance": {"type": "number", "description": "AO距离"}
                },
                "required": ["factor", "distance"]
            }
        ))
        
    def _register_render_tools(self):
        """注册渲染相关工具"""
        # 渲染设置
        self.register_tool(ToolDefinition(
            name="set_render_settings",
            description="配置渲染设置",
            category="render",
            input_schema={
                "type": "object",
                "properties": {
                    "engine": {
                        "type": "string",
                        "enum": ["CYCLES", "EEVEE"],
                        "description": "渲染引擎"
                    },
                    "samples": {"type": "integer", "description": "采样数量"},
                    "resolution_x": {"type": "integer", "description": "渲染宽度"},
                    "resolution_y": {"type": "integer", "description": "渲染高度"},
                    "use_gpu": {"type": "boolean", "description": "是否使用GPU渲染"}
                },
                "required": ["engine"]
            }
        ))
        
        # 渲染图像
        self.register_tool(ToolDefinition(
            name="render_image",
            description="渲染当前场景",
            category="render",
            input_schema={
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出文件路径"},
                    "format": {
                        "type": "string",
                        "enum": ["PNG", "JPEG", "EXR", "TIFF"],
                        "description": "输出格式"
                    },
                    "quality": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "输出质量"
                    }
                },
                "required": ["output_path", "format"]
            }
        ))
        
    def _register_modeling_tools(self):
        """注册建模相关工具"""
        # 网格编辑
        self.register_tool(ToolDefinition(
            name="edit_mesh",
            description="编辑网格几何体",
            category="modeling",
            input_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "目标对象名称"},
                    "operation": {
                        "type": "string",
                        "enum": ["SUBDIVIDE", "SMOOTH", "DECIMATE"],
                        "description": "操作类型"
                    },
                    "parameters": {"type": "object", "description": "操作参数"}
                },
                "required": ["object_name", "operation"]
            }
        ))
        
        # 修改器
        self.register_tool(ToolDefinition(
            name="add_modifier",
            description="添加对象修改器",
            category="modeling",
            input_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "目标对象名称"},
                    "modifier_type": {
                        "type": "string",
                        "enum": ["SUBSURF", "MIRROR", "ARRAY", "BOOLEAN"],
                        "description": "修改器类型"
                    },
                    "parameters": {"type": "object", "description": "修改器参数"}
                },
                "required": ["object_name", "modifier_type"]
            }
        ))
        
    def _register_animation_tools(self):
        """注册动画相关工具"""
        # 关键帧动画
        self.register_tool(ToolDefinition(
            name="create_animation",
            description="创建关键帧动画",
            category="animation",
            input_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "目标对象名称"},
                    "property": {"type": "string", "description": "动画属性"},
                    "keyframes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "frame": {"type": "integer", "description": "帧数"},
                                "value": {"type": "number", "description": "属性值"},
                                "interpolation": {
                                    "type": "string",
                                    "enum": ["LINEAR", "BEZIER", "CONSTANT"],
                                    "description": "插值方式"
                                }
                            },
                            "required": ["frame", "value"]
                        }
                    }
                },
                "required": ["object_name", "property", "keyframes"]
            }
        ))
        
        # 物理模拟
        self.register_tool(ToolDefinition(
            name="setup_physics",
            description="设置物理模拟",
            category="animation",
            input_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "目标对象名称"},
                    "physics_type": {
                        "type": "string",
                        "enum": ["RIGID_BODY", "SOFT_BODY", "CLOTH"],
                        "description": "物理类型"
                    },
                    "parameters": {"type": "object", "description": "物理参数"}
                },
                "required": ["object_name", "physics_type"]
            }
        ))

# 预定义的工具类别
TOOL_CATEGORIES = {
    "MATERIAL": "材质操作",
    "MODELING": "建模操作",
    "RENDER": "渲染操作",
    "ANIMATION": "动画操作",
    "SCENE": "场景操作"
} 