"""
BlenderMCP工具执行器

该模块负责在Blender中执行从服务器收到的工具请求。
"""

import bpy
import logging
import sys
import os
import tempfile
import json
from pathlib import Path

# 设置日志
log_file = os.path.join(tempfile.gettempdir(), "blendermcp_executor.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BlenderMCP.Executor")

# 工具处理函数映射
TOOL_HANDLERS = {}

def register_tool_handler(name, handler):
    """注册工具处理函数"""
    TOOL_HANDLERS[name] = handler
    logger.info(f"已注册工具处理函数: {name}")

# 处理从服务器接收到的请求
def process_request(request_data):
    """处理工具请求
    
    Args:
        request_data: 包含工具名称和参数的字典
        
    Returns:
        dict: 操作结果
    """
    try:
        tool_name = request_data.get("tool")
        params = request_data.get("params", {})
        
        logger.info(f"处理工具请求: {tool_name}, 参数: {params}")
        
        if tool_name in TOOL_HANDLERS:
            handler = TOOL_HANDLERS[tool_name]
            result = handler(params)
            logger.info(f"工具执行结果: {result}")
            return result
        else:
            error_msg = f"未知工具: {tool_name}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"执行工具失败: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}

def register_all_tool_handlers():
    """注册所有工具处理函数"""
    logger.info("注册所有工具处理函数")
    
    try:
        # 导入工具模块中的直接执行函数
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            # =========== 对象工具 ===========
            from blendermcp.tools.object_tools import (
                create_cube_direct,
                create_sphere_direct,
                create_cylinder_direct,
                transform_object_direct,
                delete_object_direct
            )
            
            # 注册对象工具
            register_tool_handler("create_cube", create_cube_direct)
            register_tool_handler("create_sphere", create_sphere_direct)
            register_tool_handler("create_cylinder", create_cylinder_direct)
            register_tool_handler("transform_object", transform_object_direct)
            register_tool_handler("delete_object", delete_object_direct)
            
            # =========== 场景工具 ===========
            from blendermcp.tools.scene_tools import (
                create_camera_direct,
                set_active_camera_direct,
                create_light_direct
            )
            
            # 注册场景工具
            register_tool_handler("create_camera", create_camera_direct)
            register_tool_handler("set_active_camera", set_active_camera_direct)
            register_tool_handler("create_light", create_light_direct)
            
            # =========== 材质工具 ===========
            from blendermcp.tools.material_tools import (
                create_material_direct,
                assign_material_direct,
                set_material_color_direct
            )
            
            # 注册材质工具
            register_tool_handler("create_material", create_material_direct)
            register_tool_handler("assign_material", assign_material_direct)
            register_tool_handler("set_material_color", set_material_color_direct)
            
            # =========== 动画工具 ===========
            from blendermcp.tools.animation_tools import (
                insert_keyframe_direct,
                set_animation_range_direct
            )
            
            # 注册动画工具
            register_tool_handler("insert_keyframe", insert_keyframe_direct)
            register_tool_handler("set_animation_range", set_animation_range_direct)
            
            # =========== 渲染工具 ===========
            from blendermcp.tools.render_tools import (
                set_render_engine_direct,
                set_render_resolution_direct,
                render_image_direct
            )
            
            # 注册渲染工具
            register_tool_handler("set_render_engine", set_render_engine_direct)
            register_tool_handler("set_render_resolution", set_render_resolution_direct)
            register_tool_handler("render_image", render_image_direct)
            
        except Exception as e:
            logger.error(f"导入工具模块失败: {str(e)}")
        finally:
            # 恢复sys.path
            if sys.path and sys.path[0] == os.path.dirname(os.path.dirname(os.path.abspath(__file__))):
                sys.path.pop(0)
        
    except Exception as e:
        logger.error(f"注册工具处理函数失败: {str(e)}")

# 初始化
def initialize():
    """初始化执行器"""
    # 注册工具处理函数
    register_all_tool_handlers()
    
    logger.info("执行器初始化完成")
