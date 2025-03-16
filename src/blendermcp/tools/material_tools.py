"""
BlenderMCP材质工具模块

该模块提供了与Blender材质操作相关的MCP工具函数。
"""

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

import json
from .utils import request_blender_operation, register_blender_tool

# ========== 直接执行函数（在Blender中执行） ==========

def create_material_direct(params):
    """直接创建材质(无异步)"""
    name = params.get("name", "新材质")
    color = params.get("color", [0.8, 0.8, 0.8, 1.0])
    metallic = params.get("metallic", 0.0)
    roughness = params.get("roughness", 0.5)
    
    # 检查材质是否已存在
    if name in bpy.data.materials:
        material = bpy.data.materials[name]
    else:
        material = bpy.data.materials.new(name=name)
    
    # 设置材质属性
    material.use_nodes = True
    principled_bsdf = material.node_tree.nodes.get('Principled BSDF')
    
    if principled_bsdf:
        principled_bsdf.inputs['Base Color'].default_value = color
        principled_bsdf.inputs['Metallic'].default_value = metallic
        principled_bsdf.inputs['Roughness'].default_value = roughness
    
    return {
        "status": "success", 
        "message": f"已创建材质: {name}",
        "material_name": name
    }

def assign_material_direct(params):
    """直接分配材质到对象(无异步)"""
    object_name = params.get("object_name", None)
    material_name = params.get("material_name", None)
    
    # 检查参数
    if not object_name:
        return {"status": "error", "message": "未指定对象名称"}
    if not material_name:
        return {"status": "error", "message": "未指定材质名称"}
    
    # 检查对象是否存在
    if object_name not in bpy.data.objects:
        return {"status": "error", "message": f"对象不存在: {object_name}"}
    
    # 检查材质是否存在
    if material_name not in bpy.data.materials:
        return {"status": "error", "message": f"材质不存在: {material_name}"}
    
    # 获取对象和材质
    obj = bpy.data.objects[object_name]
    material = bpy.data.materials[material_name]
    
    # 应用材质
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)
    
    return {"status": "success", "message": f"已将材质 {material_name} 应用到对象 {object_name}"}

def set_material_color_direct(params):
    """直接设置材质颜色(无异步)"""
    material_name = params.get("material_name", None)
    color = params.get("color", [0.8, 0.8, 0.8, 1.0])
    
    # 检查参数
    if not material_name:
        return {"status": "error", "message": "未指定材质名称"}
    
    # 检查材质是否存在
    if material_name not in bpy.data.materials:
        return {"status": "error", "message": f"材质不存在: {material_name}"}
    
    # 获取材质
    material = bpy.data.materials[material_name]
    
    # 设置材质颜色
    material.use_nodes = True
    principled_bsdf = material.node_tree.nodes.get('Principled BSDF')
    
    if principled_bsdf:
        principled_bsdf.inputs['Base Color'].default_value = color
    else:
        material.diffuse_color = color
    
    return {"status": "success", "message": f"已设置材质 {material_name} 的颜色为 {color}"}

# ========== 服务器端函数（通过IPC调用） ==========

def create_material(params):
    """创建材质"""
    return request_blender_operation("create_material", params)

def assign_material(params):
    """分配材质到对象"""
    return request_blender_operation("assign_material", params)

def set_material_color(params):
    """设置材质颜色"""
    return request_blender_operation("set_material_color", params)

# ========== 注册工具 ==========

def register_material_tools(adapter):
    """注册所有材质工具"""
    # 注册创建材质工具
    register_blender_tool(
        adapter,
        "create_material", 
        create_material,
        "创建材质",
        [
            {"name": "name", "type": "string", "description": "材质名称", "default": "新材质"},
            {"name": "color", "type": "array", "description": "材质颜色 [R, G, B, A]", "default": [0.8, 0.8, 0.8, 1.0]},
            {"name": "metallic", "type": "number", "description": "金属度 (0-1)", "default": 0.0},
            {"name": "roughness", "type": "number", "description": "粗糙度 (0-1)", "default": 0.5}
        ]
    )
    
    # 注册分配材质工具
    register_blender_tool(
        adapter,
        "assign_material", 
        assign_material,
        "分配材质到对象",
        [
            {"name": "object_name", "type": "string", "description": "目标对象名称", "required": True},
            {"name": "material_name", "type": "string", "description": "材质名称", "required": True}
        ]
    )
    
    # 注册设置材质颜色工具
    register_blender_tool(
        adapter,
        "set_material_color", 
        set_material_color,
        "设置材质颜色",
        [
            {"name": "material_name", "type": "string", "description": "材质名称", "required": True},
            {"name": "color", "type": "array", "description": "材质颜色 [R, G, B, A]", "default": [0.8, 0.8, 0.8, 1.0]}
        ]
    )
