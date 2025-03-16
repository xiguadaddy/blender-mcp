"""
BlenderMCP工具模块

该模块包含所有可用的MCP工具函数。
"""

import os
import json
import tempfile
import logging
from .utils import HAS_BPY, request_blender_operation

# 设置日志
logger = logging.getLogger("BlenderMCP.Tools")

def register_test_tool(adapter):
    """注册测试工具"""
    logger.info("注册测试工具")
    
    async def test_echo(params):
        """回显输入参数"""
        logger.info(f"测试工具被调用: {params}")
        return {"echo": params}
    
    adapter.register_tool(
        "blender.test.echo", 
        test_echo,
        "回显输入参数",
        [{"name": "message", "type": "string", "description": "要回显的消息"}]
    )
    logger.info("测试工具注册完成")

def register_all_tools(adapter):
    """注册所有工具到MCP适配器"""
    logger.info("开始注册所有工具")
    
    # 首先注册测试工具
    register_test_tool(adapter)
    
    # 然后注册其他工具
    try:
        from .object_tools import register_object_tools
        from .material_tools import register_material_tools
        from .scene_tools import register_scene_tools
        from .render_tools import register_render_tools
        from .animation_tools import register_animation_tools
        
        # 注册所有工具
        register_object_tools(adapter)
        register_material_tools(adapter)
        register_scene_tools(adapter)
        register_render_tools(adapter)
        register_animation_tools(adapter)
        
        logger.info("所有工具注册完成")
    except Exception as e:
        logger.error(f"注册工具时出错: {str(e)}")
        logger.info("只有测试工具被注册")

def get_tools_info():
    """获取所有工具的信息
    
    Returns:
        list: 包含所有工具信息的列表
    """
    try:
        # 尝试从临时文件读取
        tools_file = os.path.join(tempfile.gettempdir(), "blendermcp_tools.json")
        if os.path.exists(tools_file):
            try:
                with open(tools_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"读取工具列表文件失败: {str(e)}")
        
        # 如果文件不存在或读取失败，创建一个基本的工具信息列表
        # 对象工具
        object_tools = [
            {
                "name": "blender.object.create_cube",
                "description": "在场景中创建一个立方体",
                "parameters": [
                    {"name": "size", "type": "number", "description": "立方体的大小", "default": 2.0},
                    {"name": "location", "type": "array", "description": "立方体的位置 [x, y, z]", "default": [0, 0, 0]}
                ]
            },
            {
                "name": "blender.object.create_sphere",
                "description": "在场景中创建一个球体",
                "parameters": [
                    {"name": "radius", "type": "number", "description": "球体的半径", "default": 1.0},
                    {"name": "location", "type": "array", "description": "球体的位置 [x, y, z]", "default": [0, 0, 0]}
                ]
            },
            {
                "name": "blender.object.create_cylinder",
                "description": "在场景中创建一个圆柱体",
                "parameters": [
                    {"name": "radius", "type": "number", "description": "圆柱体的半径", "default": 1.0},
                    {"name": "depth", "type": "number", "description": "圆柱体的深度", "default": 2.0},
                    {"name": "location", "type": "array", "description": "圆柱体的位置 [x, y, z]", "default": [0, 0, 0]}
                ]
            }
        ]
        
        # 场景工具
        scene_tools = [
            {
                "name": "blender.scene.create_camera",
                "description": "在场景中创建一个相机",
                "parameters": [
                    {"name": "name", "type": "string", "description": "相机名称", "default": "新相机"},
                    {"name": "location", "type": "array", "description": "相机位置 [x, y, z]", "default": [0, 0, 0]}
                ]
            },
            {
                "name": "blender.scene.create_light",
                "description": "在场景中创建一个灯光",
                "parameters": [
                    {"name": "name", "type": "string", "description": "灯光名称", "default": "新灯光"},
                    {"name": "type", "type": "string", "description": "灯光类型", "default": "POINT"},
                    {"name": "location", "type": "array", "description": "灯光位置 [x, y, z]", "default": [0, 0, 0]}
                ]
            }
        ]
        
        # 合并所有工具
        all_tools = object_tools + scene_tools
        
        # 按名称排序
        all_tools.sort(key=lambda x: x["name"])
        
        return all_tools
        
    except Exception as e:
        logger.error(f"获取工具信息失败: {str(e)}")
        return []

__all__ = ['register_all_tools', 'get_tools_info']