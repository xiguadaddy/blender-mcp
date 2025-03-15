"""
BlenderMCP Addon
"""

import bpy
import logging
from .panels import register_panels, unregister_panels
from .properties import register_properties, unregister_properties
from .operators import register_operators, unregister_operators

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bl_info = {
    "name": "BlenderMCP",
    "description": "Blender MCP Server",
    "author": "Your Name",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "warning": "",
    "doc_url": "",
    "category": "Development"
}

def register():
    """Register the addon"""
    logger.info("正在注册 BlenderMCP 插件...")
    try:
        # 注册属性
        register_properties()
        
        # 注册操作符
        register_operators()
        
        # 注册面板
        register_panels()
        
        logger.info("BlenderMCP 插件注册完成")
    except Exception as e:
        logger.error(f"插件注册失败: {str(e)}")
        raise

def unregister():
    """Unregister the addon"""
    logger.info("正在注销 BlenderMCP 插件...")
    try:
        # 注销面板
        unregister_panels()
        
        # 注销操作符
        unregister_operators()
        
        # 注销属性
        unregister_properties()
        
        logger.info("BlenderMCP 插件注销完成")
    except Exception as e:
        logger.error(f"插件注销失败: {str(e)}")
        raise

if __name__ == "__main__":
    register() 