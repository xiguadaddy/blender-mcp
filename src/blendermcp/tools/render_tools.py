"""
BlenderMCP渲染工具模块

该模块提供了与Blender渲染相关的MCP工具函数。
"""

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

import json
import tempfile
import os
from pathlib import Path
from .utils import request_blender_operation, register_blender_tool

# ========== 直接执行函数（在Blender中执行） ==========

def render_image_direct(params):
    """直接渲染图像(无异步)"""
    resolution_x = params.get("resolution_x", 1920)
    resolution_y = params.get("resolution_y", 1080)
    file_path = params.get("file_path", None)
    file_format = params.get("file_format", "PNG")
    samples = params.get("samples", 128)
    
    # 如果未指定文件路径，则使用临时文件
    if not file_path:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "blender_render.png")
    
    # 设置渲染参数
    scene = bpy.context.scene
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = file_format
    
    # 设置引擎特定参数
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = samples
    
    # 设置输出路径
    scene.render.filepath = file_path
    
    # 渲染图像
    bpy.ops.render.render(write_still=True)
    
    return {
        "status": "success", 
        "message": f"已渲染图像，保存到: {file_path}", 
        "file_path": file_path
    }

def set_render_engine_direct(params):
    """直接设置渲染引擎(无异步)"""
    engine = params.get("engine", "CYCLES")
    
    # 设置渲染引擎
    bpy.context.scene.render.engine = engine
    
    # 针对不同引擎进行特定设置
    if engine == 'CYCLES':
        device = params.get("device", "GPU")
        if device == "GPU":
            bpy.context.scene.cycles.device = 'GPU'
            
            # 尝试启用所有可用的GPU设备
            try:
                preferences = bpy.context.preferences
                cycles_preferences = preferences.addons['cycles'].preferences
                
                # 启用CUDA设备
                cycles_preferences.compute_device_type = 'CUDA'
                
                for device in cycles_preferences.devices:
                    device.use = True
            except Exception as e:
                return {
                    "status": "warning", 
                    "message": f"已设置渲染引擎为: {engine}，但启用GPU设备时出错: {str(e)}"
                }
        else:
            bpy.context.scene.cycles.device = 'CPU'
    
    return {
        "status": "success", 
        "message": f"已设置渲染引擎为: {engine}，设备: {device if engine == 'CYCLES' else 'N/A'}"
    }

def set_render_resolution_direct(params):
    """直接设置渲染分辨率(无异步)"""
    resolution_x = params.get("resolution_x", 1920)
    resolution_y = params.get("resolution_y", 1080)
    percentage = params.get("percentage", 100)
    
    # 设置渲染分辨率
    scene = bpy.context.scene
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = percentage
    
    return {
        "status": "success", 
        "message": f"已设置渲染分辨率为: {resolution_x}x{resolution_y} ({percentage}%)"
    }

# ========== 服务器端函数（通过IPC调用） ==========

def render_image(params):
    """渲染图像"""
    return request_blender_operation("render_image", params)

def set_render_engine(params):
    """设置渲染引擎"""
    return request_blender_operation("set_render_engine", params)

def set_render_resolution(params):
    """设置渲染分辨率"""
    return request_blender_operation("set_render_resolution", params)

# ========== 注册工具 ==========

def register_render_tools(adapter):
    """注册所有渲染工具"""
    # 注册渲染图像工具
    register_blender_tool(
        adapter,
        "render_image", 
        render_image,
        "渲染图像",
        [
            {"name": "resolution_x", "type": "integer", "description": "渲染宽度（像素）", "default": 1920},
            {"name": "resolution_y", "type": "integer", "description": "渲染高度（像素）", "default": 1080},
            {"name": "file_path", "type": "string", "description": "输出文件路径"},
            {"name": "file_format", "type": "string", "description": "输出格式 (PNG, JPEG, EXR)", "default": "PNG"},
            {"name": "samples", "type": "integer", "description": "渲染采样数", "default": 128}
        ]
    )
    
    # 注册设置渲染引擎工具
    register_blender_tool(
        adapter,
        "set_render_engine", 
        set_render_engine,
        "设置渲染引擎",
        [
            {"name": "engine", "type": "string", "description": "渲染引擎 (CYCLES, BLENDER_EEVEE, WORKBENCH)", "default": "CYCLES"},
            {"name": "device", "type": "string", "description": "计算设备 (CPU, GPU)", "default": "GPU"}
        ]
    )
    
    # 注册设置渲染分辨率工具
    register_blender_tool(
        adapter,
        "set_render_resolution", 
        set_render_resolution,
        "设置渲染分辨率",
        [
            {"name": "resolution_x", "type": "integer", "description": "渲染宽度（像素）", "default": 1920},
            {"name": "resolution_y", "type": "integer", "description": "渲染高度（像素）", "default": 1080},
            {"name": "percentage", "type": "integer", "description": "渲染比例百分比", "default": 100}
        ]
    )
