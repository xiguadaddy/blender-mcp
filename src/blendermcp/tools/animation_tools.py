"""
BlenderMCP动画工具模块

该模块提供了与Blender动画相关的MCP工具函数。
"""

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

import json
from .utils import request_blender_operation, register_blender_tool

# ========== 直接执行函数（在Blender中执行） ==========

def insert_keyframe_direct(params):
    """直接插入关键帧(无异步)"""
    object_name = params.get("object_name", None)
    frame = params.get("frame", bpy.context.scene.frame_current)
    location = params.get("location", None)
    rotation = params.get("rotation", None)
    scale = params.get("scale", None)
    
    if not object_name or object_name not in bpy.data.objects:
        return {"status": "error", "message": f"对象不存在: {object_name}"}
    
    obj = bpy.data.objects[object_name]
    
    # 设置当前帧
    bpy.context.scene.frame_set(frame)
    
    # 设置位置、旋转和缩放
    if location is not None:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame)
    
    if rotation is not None:
        if len(rotation) == 3:
            obj.rotation_euler = rotation
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        elif len(rotation) == 4:
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = rotation
            obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)
    
    return {
        "status": "success", 
        "message": f"已为对象 {object_name} 在帧 {frame} 设置关键帧",
        "frame": frame
    }

def set_animation_range_direct(params):
    """直接设置动画范围(无异步)"""
    start_frame = params.get("start_frame", 1)
    end_frame = params.get("end_frame", 250)
    current_frame = params.get("current_frame", start_frame)
    
    # 设置场景的帧范围
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = end_frame
    scene.frame_current = current_frame
    
    return {
        "status": "success", 
        "message": f"已设置动画范围: {start_frame}-{end_frame}, 当前帧: {current_frame}",
        "start_frame": start_frame,
        "end_frame": end_frame,
        "current_frame": current_frame
    }

def create_animation_direct(params):
    """直接创建简单动画(无异步)"""
    object_name = params.get("object_name", None)
    animation_type = params.get("type", "LOCATION")
    start_frame = params.get("start_frame", 1)
    end_frame = params.get("end_frame", 100)
    start_value = params.get("start_value", [0, 0, 0])
    end_value = params.get("end_value", [0, 0, 10])
    
    if not object_name or object_name not in bpy.data.objects:
        return {"status": "error", "message": f"对象不存在: {object_name}"}
    
    obj = bpy.data.objects[object_name]
    
    # 设置开始关键帧
    bpy.context.scene.frame_set(start_frame)
    
    if animation_type == "LOCATION":
        obj.location = start_value
        obj.keyframe_insert(data_path="location", frame=start_frame)
    elif animation_type == "ROTATION":
        obj.rotation_euler = start_value
        obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    elif animation_type == "SCALE":
        obj.scale = start_value
        obj.keyframe_insert(data_path="scale", frame=start_frame)
    else:
        return {"status": "error", "message": f"不支持的动画类型: {animation_type}"}
    
    # 设置结束关键帧
    bpy.context.scene.frame_set(end_frame)
    
    if animation_type == "LOCATION":
        obj.location = end_value
        obj.keyframe_insert(data_path="location", frame=end_frame)
    elif animation_type == "ROTATION":
        obj.rotation_euler = end_value
        obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)
    elif animation_type == "SCALE":
        obj.scale = end_value
        obj.keyframe_insert(data_path="scale", frame=end_frame)
    
    return {
        "status": "success", 
        "message": f"已为对象 {object_name} 创建 {animation_type} 动画",
        "object_name": object_name,
        "type": animation_type,
        "start_frame": start_frame,
        "end_frame": end_frame
    }

# ========== 服务器端函数（通过IPC调用） ==========

def insert_keyframe(params):
    """插入关键帧"""
    return request_blender_operation("insert_keyframe", params)

def set_animation_range(params):
    """设置动画范围"""
    return request_blender_operation("set_animation_range", params)

def create_animation(params):
    """创建简单动画"""
    return request_blender_operation("create_animation", params)

# ========== 注册工具 ==========

def register_animation_tools(adapter):
    """注册所有动画工具"""
    # 注册插入关键帧工具
    register_blender_tool(
        adapter,
        "insert_keyframe", 
        insert_keyframe,
        "插入关键帧",
        [
            {"name": "object_name", "type": "string", "description": "目标对象名称", "required": True},
            {"name": "frame", "type": "integer", "description": "关键帧帧数", "default": "current"},
            {"name": "location", "type": "array", "description": "位置 [x, y, z]"},
            {"name": "rotation", "type": "array", "description": "旋转 [x, y, z] 或四元数 [w, x, y, z]"},
            {"name": "scale", "type": "array", "description": "缩放 [x, y, z]"}
        ]
    )
    
    # 注册设置动画范围工具
    register_blender_tool(
        adapter,
        "set_animation_range", 
        set_animation_range,
        "设置动画范围",
        [
            {"name": "start_frame", "type": "integer", "description": "开始帧", "default": 1},
            {"name": "end_frame", "type": "integer", "description": "结束帧", "default": 250},
            {"name": "current_frame", "type": "integer", "description": "当前帧", "default": 1}
        ]
    )
    
    # 注册创建简单动画工具
    register_blender_tool(
        adapter,
        "create_animation", 
        create_animation,
        "创建简单动画",
        [
            {"name": "object_name", "type": "string", "description": "目标对象名称", "required": True},
            {"name": "type", "type": "string", "description": "动画类型 (LOCATION, ROTATION, SCALE)", "default": "LOCATION"},
            {"name": "start_frame", "type": "integer", "description": "开始帧", "default": 1},
            {"name": "end_frame", "type": "integer", "description": "结束帧", "default": 100},
            {"name": "start_value", "type": "array", "description": "开始值 [x, y, z]", "default": [0, 0, 0]},
            {"name": "end_value", "type": "array", "description": "结束值 [x, y, z]", "default": [0, 0, 10]}
        ]
    )
