"""BlenderMCP API规范定义模块"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

API_VERSION = "1.0.0"

class APICategory(Enum):
    """API类别"""
    OBJECT = "object"       # 对象操作
    MATERIAL = "material"   # 材质操作
    LIGHT = "light"        # 灯光操作
    RENDER = "render"      # 渲染操作
    ANIMATION = "animation" # 动画操作
    PHYSICS = "physics"    # 物理模拟
    SCENE = "scene"       # 场景操作

@dataclass
class APIEndpoint:
    """API端点定义"""
    name: str
    category: APICategory
    description: str
    version: str = API_VERSION
    deprecated: bool = False
    input_schema: Dict[str, Any] = None
    output_schema: Dict[str, Any] = None

# 标准参数定义
PARAM_SCHEMAS = {
    # 通用参数
    "object_name": {
        "type": "string",
        "description": "对象名称",
        "minLength": 1
    },
    "location": {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 3,
        "maxItems": 3,
        "description": "位置坐标(X,Y,Z)"
    },
    "rotation": {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 3,
        "maxItems": 3,
        "description": "旋转角度(X,Y,Z)"
    },
    "scale": {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 3,
        "maxItems": 3,
        "description": "缩放比例(X,Y,Z)"
    },
    
    # 材质参数
    "material_name": {
        "type": "string",
        "description": "材质名称"
    },
    "color": {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 4,
        "maxItems": 4,
        "description": "RGBA颜色值"
    },
    
    # 灯光参数
    "light_type": {
        "type": "string",
        "enum": ["POINT", "SUN", "SPOT", "AREA"],
        "description": "灯光类型"
    },
    "energy": {
        "type": "number",
        "minimum": 0,
        "description": "灯光强度"
    },
    
    # 渲染参数
    "resolution": {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "minimum": 1},
            "y": {"type": "integer", "minimum": 1}
        },
        "required": ["x", "y"],
        "description": "渲染分辨率"
    },
    "samples": {
        "type": "integer",
        "minimum": 1,
        "description": "渲染采样数"
    }
}

# API端点定义
ENDPOINTS = {
    # 对象操作
    "create_object": APIEndpoint(
        name="create_object",
        category=APICategory.OBJECT,
        description="创建新对象",
        input_schema={
            "type": "object",
            "properties": {
                "object_type": {"type": "string", "enum": ["MESH", "CURVE", "LIGHT", "CAMERA"]},
                "object_name": PARAM_SCHEMAS["object_name"],
                "location": PARAM_SCHEMAS["location"],
                "rotation": PARAM_SCHEMAS["rotation"],
                "scale": PARAM_SCHEMAS["scale"]
            },
            "required": ["object_type"]
        }
    ),
    
    # 材质操作
    "set_material": APIEndpoint(
        name="set_material",
        category=APICategory.MATERIAL,
        description="设置对象材质",
        input_schema={
            "type": "object",
            "properties": {
                "object_name": PARAM_SCHEMAS["object_name"],
                "material_name": PARAM_SCHEMAS["material_name"],
                "color": PARAM_SCHEMAS["color"]
            },
            "required": ["object_name"]
        }
    ),
    
    # 灯光操作
    "create_light": APIEndpoint(
        name="create_light",
        category=APICategory.LIGHT,
        description="创建灯光",
        input_schema={
            "type": "object",
            "properties": {
                "light_type": PARAM_SCHEMAS["light_type"],
                "object_name": PARAM_SCHEMAS["object_name"],
                "location": PARAM_SCHEMAS["location"],
                "energy": PARAM_SCHEMAS["energy"],
                "color": PARAM_SCHEMAS["color"]
            },
            "required": ["light_type"]
        }
    ),
    
    # 渲染操作
    "render_image": APIEndpoint(
        name="render_image",
        category=APICategory.RENDER,
        description="渲染图像",
        input_schema={
            "type": "object",
            "properties": {
                "resolution": PARAM_SCHEMAS["resolution"],
                "samples": PARAM_SCHEMAS["samples"],
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径"
                }
            },
            "required": ["output_path"]
        }
    ),
    
    # 场景操作
    "get_scene_info": APIEndpoint(
        name="get_scene_info",
        category=APICategory.SCENE,
        description="获取场景信息",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    
    "get_object_info": APIEndpoint(
        name="get_object_info",
        category=APICategory.OBJECT,
        description="获取对象信息",
        input_schema={
            "type": "object",
            "properties": {
                "object_name": PARAM_SCHEMAS["object_name"]
            },
            "required": ["object_name"]
        }
    ),
    
    "delete_object": APIEndpoint(
        name="delete_object",
        category=APICategory.OBJECT,
        description="删除对象",
        input_schema={
            "type": "object",
            "properties": {
                "object_name": PARAM_SCHEMAS["object_name"]
            },
            "required": ["object_name"]
        }
    )
}

def get_endpoint(name: str) -> Optional[APIEndpoint]:
    """获取API端点定义"""
    return ENDPOINTS.get(name)

def validate_version(version: str) -> bool:
    """验证API版本兼容性"""
    current = tuple(map(int, API_VERSION.split('.')))
    target = tuple(map(int, version.split('.')))
    return target <= current

def get_deprecated_endpoints() -> List[APIEndpoint]:
    """获取已废弃的端点"""
    return [ep for ep in ENDPOINTS.values() if ep.deprecated] 