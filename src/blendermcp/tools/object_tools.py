"""
BlenderMCP对象工具模块

该模块提供了与Blender对象操作相关的MCP工具函数。
"""

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

import json
from .utils import request_blender_operation, register_blender_tool

# 如果不在Blender环境中，尝试导入IPC模块
if not HAS_BPY:
    try:
        from blendermcp.common.ipc import send_request_to_blender
    except ImportError:
        # 如果导入失败，提供一个空的占位实现
        async def send_request_to_blender(request):
            return {"status": "error", "message": "IPC模块未正确初始化"}

# ========== 直接执行函数（在Blender中执行） ==========

def create_cube_direct(params):
    """直接创建立方体(无异步)"""
    size = params.get("size", 2.0)
    location = params.get("location", [0, 0, 0])
    
    bpy.ops.mesh.primitive_cube_add(size=size, location=tuple(location))
    obj = bpy.context.active_object
    
    return {
        "status": "success", 
        "message": f"已创建立方体，大小: {size}，位置: {location}",
        "object_name": obj.name
    }

def create_sphere_direct(params):
    """直接创建球体(无异步)"""
    radius = params.get("radius", 1.0)
    location = params.get("location", [0, 0, 0])
    segments = params.get("segments", 32)
    rings = params.get("rings", 16)
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=tuple(location), 
                                        segments=segments, ring_count=rings)
    obj = bpy.context.active_object
    
    return {
        "status": "success", 
        "message": f"已创建球体，半径: {radius}，位置: {location}",
        "object_name": obj.name
    }

def create_cylinder_direct(params):
    """直接创建圆柱体(无异步)"""
    radius = params.get("radius", 1.0)
    depth = params.get("depth", 2.0)
    location = params.get("location", [0, 0, 0])
    vertices = params.get("vertices", 32)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, 
                                      vertices=vertices, location=tuple(location))
    obj = bpy.context.active_object
    
    return {
        "status": "success", 
        "message": f"已创建圆柱体，半径: {radius}，深度: {depth}，位置: {location}",
        "object_name": obj.name
    }

def transform_object_direct(params):
    """直接变换对象(无异步)"""
    object_name = params.get("object_name", None)
    location = params.get("location", None)
    rotation = params.get("rotation", None)
    scale = params.get("scale", None)
    
    if not object_name or object_name not in bpy.data.objects:
        return {"status": "error", "message": f"对象不存在: {object_name}"}
    
    obj = bpy.data.objects[object_name]
    
    if location:
        obj.location = location
    if rotation:
        obj.rotation_euler = rotation
    if scale:
        obj.scale = scale
    
    return {"status": "success", "message": f"已变换对象: {object_name}"}

def delete_object_direct(params):
    """直接删除对象(无异步)"""
    object_name = params.get("object_name", None)
    
    if not object_name or object_name not in bpy.data.objects:
        return {"status": "error", "message": f"对象不存在: {object_name}"}
    
    # 获取对象并删除
    obj = bpy.data.objects[object_name]
    bpy.data.objects.remove(obj)
    
    return {"status": "success", "message": f"已删除对象: {object_name}"}

# ========== 服务器端函数（通过IPC调用） ==========

def create_cube(params):
    """创建立方体"""
    return request_blender_operation("create_cube", params)

def create_sphere(params):
    """创建球体"""
    return request_blender_operation("create_sphere", params)

def create_cylinder(params):
    """创建圆柱体"""
    return request_blender_operation("create_cylinder", params)

def transform_object(params):
    """变换对象"""
    return request_blender_operation("transform_object", params)

def delete_object(params):
    """删除对象"""
    return request_blender_operation("delete_object", params)

# ========== 注册工具 ==========

def register_object_tools(adapter):
    """注册所有对象工具"""
    # 注册创建立方体工具
    register_blender_tool(
        adapter,
        "create_cube", 
        create_cube,
        "创建立方体",
        [
            {"name": "size", "type": "number", "description": "立方体大小", "default": 2.0},
            {"name": "location", "type": "array", "description": "立方体位置 [x, y, z]", "default": [0, 0, 0]}
        ]
    )
    
    # 注册创建球体工具
    register_blender_tool(
        adapter,
        "create_sphere", 
        create_sphere,
        "创建球体",
        [
            {"name": "radius", "type": "number", "description": "球体半径", "default": 1.0},
            {"name": "location", "type": "array", "description": "球体位置 [x, y, z]", "default": [0, 0, 0]},
            {"name": "segments", "type": "number", "description": "经线段数", "default": 32},
            {"name": "rings", "type": "number", "description": "纬线环数", "default": 16}
        ]
    )
    
    # 注册创建圆柱体工具
    register_blender_tool(
        adapter,
        "create_cylinder", 
        create_cylinder,
        "创建圆柱体",
        [
            {"name": "radius", "type": "number", "description": "圆柱体半径", "default": 1.0},
            {"name": "depth", "type": "number", "description": "圆柱体高度", "default": 2.0},
            {"name": "location", "type": "array", "description": "圆柱体位置 [x, y, z]", "default": [0, 0, 0]},
            {"name": "vertices", "type": "number", "description": "圆周顶点数", "default": 32}
        ]
    )
    
    # 注册变换对象工具
    register_blender_tool(
        adapter,
        "transform_object", 
        transform_object,
        "变换对象",
        [
            {"name": "object_name", "type": "string", "description": "对象名称", "required": True},
            {"name": "location", "type": "array", "description": "位置 [x, y, z]"},
            {"name": "rotation", "type": "array", "description": "旋转 [x, y, z]"},
            {"name": "scale", "type": "array", "description": "缩放 [x, y, z]"}
        ]
    )
    
    # 注册删除对象工具
    register_blender_tool(
        adapter,
        "delete_object", 
        delete_object,
        "删除对象",
        [
            {"name": "object_name", "type": "string", "description": "对象名称", "required": True}
        ]
    )
