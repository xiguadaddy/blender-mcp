"""
BlenderMCP工具辅助函数

该模块提供工具模块使用的辅助函数。
"""

import json
import logging
import tempfile
import os

# 设置日志
log_file = os.path.join(tempfile.gettempdir(), "blendermcp_tools.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BlenderMCP.Tools")

# 判断是否在Blender环境中运行
try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    
    # 如果不在Blender环境中，尝试导入IPC模块
    try:
        from blendermcp.common.ipc import send_request_to_blender
    except ImportError:
        # 如果导入失败，提供一个空的占位实现
        def send_request_to_blender(request):
            return {"status": "error", "message": "IPC模块未正确初始化"}

def request_blender_operation(tool_name, params):
    """
    向Blender请求执行操作，使用IPC
    
    Args:
        tool_name: 工具名称
        params: 工具参数
        
    Returns:
        dict: 操作结果
    """
    # 如果在Blender环境中直接运行，这个函数不应被调用
    if HAS_BPY:
        logger.warning(f"在Blender环境中直接调用了request_blender_operation函数: {tool_name}")
        return {"status": "error", "message": "在Blender环境中不应直接调用此函数"}
        
    # 构建请求
    request = {
        "tool": tool_name,
        "params": params
    }
    
    # 使用IPC发送请求
    response = send_request_to_blender(request)
    return response

def register_blender_tool(adapter, name, handler, description, parameters):
    """
    注册Blender工具
    
    Args:
        adapter: MCP适配器
        name: 工具名称
        handler: 处理函数
        description: 工具描述
        parameters: 工具参数列表
    """
    # 确保工具名称有blender.前缀
    if not name.startswith("blender."):
        name = f"blender.{name}"
        
    adapter.register_tool(
        name,
        handler,
        description,
        parameters
    )
    
    logger.info(f"已注册Blender工具: {name}") 