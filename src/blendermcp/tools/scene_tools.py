"""
BlenderMCP场景工具模块

该模块提供了与Blender场景操作相关的MCP工具函数。
"""

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

import json
from .utils import request_blender_operation, register_blender_tool

# ========== 直接执行函数（在Blender中执行） ==========

def create_camera_direct(params):
    """直接创建相机(无异步)"""
    location = params.get("location", [0, 0, 0])
    rotation = params.get("rotation", [0, 0, 0])
    name = params.get("name", "Camera")
    
    # 创建相机数据
    camera_data = bpy.data.cameras.new(name=name)
    
    # 创建相机对象
    camera_obj = bpy.data.objects.new(name, camera_data)
    
    # 设置位置和旋转
    camera_obj.location = location
    camera_obj.rotation_euler = rotation
    
    # 添加到场景
    bpy.context.collection.objects.link(camera_obj)
    
    return {
        "status": "success", 
        "message": f"已创建相机: {name}",
        "object_name": name
    }

def set_active_camera_direct(params):
    """直接设置活动相机(无异步)"""
    camera_name = params.get("camera_name", None)
    
    if not camera_name or camera_name not in bpy.data.objects:
        return {"status": "error", "message": f"相机不存在: {camera_name}"}
    
    camera_obj = bpy.data.objects[camera_name]
    
    # 检查对象是否为相机
    if camera_obj.type != 'CAMERA':
        return {"status": "error", "message": f"对象不是相机: {camera_name}"}
    
    # 设置活动相机
    bpy.context.scene.camera = camera_obj
    
    return {"status": "success", "message": f"已设置活动相机: {camera_name}"}

def create_light_direct(params):
    """直接创建光源(无异步)"""
    light_type = params.get("type", "POINT")
    location = params.get("location", [0, 0, 0])
    rotation = params.get("rotation", [0, 0, 0])
    energy = params.get("energy", 1000.0)
    color = params.get("color", [1.0, 1.0, 1.0])
    name = params.get("name", "Light")
    
    # 验证光源类型
    valid_types = ['POINT', 'SUN', 'SPOT', 'AREA']
    if light_type not in valid_types:
        return {"status": "error", "message": f"无效的光源类型: {light_type}，有效类型: {valid_types}"}
    
    # 创建光源数据
    light_data = bpy.data.lights.new(name=name, type=light_type)
    
    # 设置光源属性
    light_data.energy = energy
    light_data.color = color
    
    # 创建光源对象
    light_obj = bpy.data.objects.new(name, light_data)
    
    # 设置位置和旋转
    light_obj.location = location
    light_obj.rotation_euler = rotation
    
    # 添加到场景
    bpy.context.collection.objects.link(light_obj)
    
    return {
        "status": "success", 
        "message": f"已创建{light_type}光源: {name}",
        "object_name": name
    }

# ========== 服务器端函数（通过IPC调用） ==========

def create_camera(params):
    """创建相机"""
    return request_blender_operation("create_camera", params)

def set_active_camera(params):
    """设置活动相机"""
    return request_blender_operation("set_active_camera", params)

def create_light(params):
    """创建光源"""
    return request_blender_operation("create_light", params)

# ========== 注册工具 ==========

def register_scene_tools(adapter):
    """注册所有场景工具"""
    # 注册创建相机工具
    register_blender_tool(
        adapter,
        "create_camera", 
        create_camera,
        "创建相机",
        [
            {"name": "location", "type": "array", "description": "相机位置 [x, y, z]", "default": [0, 0, 0]},
            {"name": "rotation", "type": "array", "description": "相机旋转 [x, y, z]", "default": [0, 0, 0]},
            {"name": "name", "type": "string", "description": "相机名称", "default": "Camera"}
        ]
    )
    
    # 注册设置活动相机工具
    register_blender_tool(
        adapter,
        "set_active_camera", 
        set_active_camera,
        "设置活动相机",
        [
            {"name": "camera_name", "type": "string", "description": "相机名称", "required": True}
        ]
    )
    
    # 注册创建光源工具
    register_blender_tool(
        adapter,
        "create_light", 
        create_light,
        "创建光源",
        [
            {"name": "type", "type": "string", "description": "光源类型 (POINT, SUN, SPOT, AREA)", "default": "POINT"},
            {"name": "location", "type": "array", "description": "光源位置 [x, y, z]", "default": [0, 0, 0]},
            {"name": "rotation", "type": "array", "description": "光源旋转 [x, y, z]", "default": [0, 0, 0]},
            {"name": "energy", "type": "number", "description": "光源强度", "default": 1000.0},
            {"name": "color", "type": "array", "description": "光源颜色 [r, g, b]", "default": [1.0, 1.0, 1.0]},
            {"name": "name", "type": "string", "description": "光源名称", "default": "Light"}
        ]
    )
