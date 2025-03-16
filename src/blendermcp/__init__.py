"""
BlenderMCP - Blender的多模态控制协议

该模块允许AI助手和其他工具通过MCP协议控制Blender。
"""

import os
import sys
import bpy
import logging
import subprocess
import tempfile
import importlib.util
from pathlib import Path

# 插件信息
bl_info = {
    "name": "BlenderMCP",
    "author": "BlenderMCP Team",
    "description": "Blender的多模态控制协议（MCP）",
    "blender": (2, 80, 0),
    "version": (0, 3, 0),
    "location": "View3D > Sidebar > MCP",
    "warning": "",
    "category": "Interface"
}

# 配置日志
log_dir = os.path.join(tempfile.gettempdir(), "blendermcp")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "blendermcp_addon.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blendermcp")

# 设置库安装目录
LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
os.makedirs(LIB_DIR, exist_ok=True)
sys.path.insert(0, LIB_DIR)

# 获取当前模块的路径和项目根目录
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(ADDON_DIR)))

# 检查并安装依赖项
def ensure_dependencies():
    """确保所有依赖项都已安装"""
    try:
        # 尝试导入关键依赖
        import websocket
        logger.info("websocket-client已安装")
    except ImportError:
        logger.warning("websocket-client未安装，正在尝试安装...")
        try:
            # 查找requirements.txt
            requirements_file = os.path.join(ROOT_DIR, "requirements.txt")
            if not os.path.exists(requirements_file):
                logger.warning(f"无法找到requirements.txt: {requirements_file}")
                # 创建一个基本的requirements.txt
                requirements_file = os.path.join(tempfile.gettempdir(), "blendermcp_requirements.txt")
                with open(requirements_file, 'w') as f:
                    f.write("websocket-client>=1.8.0\nwebsocket-server>=0.6.1\n")
            
            # 使用pip安装依赖
            python_exe = sys.executable
            cmd = [
                python_exe, "-m", "pip", "install",
                "--target", LIB_DIR,
                "-r", requirements_file
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"安装依赖失败: {result.stderr}")
                # 尝试单独安装关键依赖
                try:
                    subprocess.run(
                        [python_exe, "-m", "pip", "install", "--target", LIB_DIR, "websocket-client>=1.8.0"],
                        check=True
                    )
                    logger.info("已安装websocket-client")
                except Exception as e:
                    logger.error(f"安装websocket-client失败: {e}")
            else:
                logger.info("依赖项安装成功")
                
            # 重新加入路径并重新导入
            if LIB_DIR not in sys.path:
                sys.path.insert(0, LIB_DIR)
                
        except Exception as e:
            logger.error(f"安装依赖项时出错: {e}")

# 从addon子模块导入
try:
    from .addon import (
        panels,
        preferences, 
        properties,
        server_operators,
        tool_viewer,
        request_listener
    )
    # 标记模块是否已导入
    HAS_ADDON_MODULES = True
except ImportError as e:
    logger.error(f"导入addon子模块失败: {e}")
    HAS_ADDON_MODULES = False


# 注册函数
def register():
    """注册插件"""
    logger.info("注册BlenderMCP插件...")
    
    # 确保依赖项已安装
    ensure_dependencies()
    
    # 注册各个模块
    if HAS_ADDON_MODULES:
        preferences.register()
        properties.register()
        panels.register()
        server_operators.register()
        tool_viewer.register()
        
        # 启动服务器
        bpy.app.timers.register(start_server_delayed, first_interval=1.0)
    
    logger.info("BlenderMCP插件注册完成")

# 注销函数
def unregister():
    """注销插件"""
    logger.info("注销BlenderMCP插件...")
    
    # 停止服务器
    if HAS_ADDON_MODULES:
        try:
            if request_listener.is_running():
                request_listener.stop()
            server_operators.stop_server()
        except Exception as e:
            logger.error(f"停止服务器时出错: {e}")
        
        # 注销各个模块
        try:
            tool_viewer.unregister()
            server_operators.unregister()
            panels.unregister()
            properties.unregister()
            preferences.unregister()
        except Exception as e:
            logger.error(f"注销模块时出错: {e}")
        
        # 移除定时器
        try:
            bpy.app.timers.unregister(start_server_delayed)
        except:
            pass
    
    logger.info("BlenderMCP插件注销完成")

# 延迟启动服务器的函数
def start_server_delayed():
    """延迟启动服务器，确保在Blender完全加载后启动"""
    try:
        # 获取偏好设置
        addon_prefs = preferences.get_addon_preferences(bpy.context)
        
        # 检查是否自动启动服务器
        if addon_prefs.auto_start_server:
            logger.info("自动启动MCP服务器...")
            
            # 启动服务器
            if addon_prefs.server_mode == 'WEBSOCKET':
                host = addon_prefs.websocket_host
                port = addon_prefs.websocket_port
                success, message = server_operators.start_server(host=host, port=port, debug=True)
            else:
                success, message = server_operators.start_server(host='localhost', port=0, debug=True)
                
            if success:
                logger.info(f"MCP服务器已自动启动: {message}")
                
                # 启动请求监听器
                if not request_listener.is_running():
                    success = request_listener.start()
                    if success:
                        logger.info("请求监听器已启动")
                    else:
                        logger.error("请求监听器启动失败")
            else:
                logger.error(f"MCP服务器自动启动失败: {message}")
                
                # 添加一个按钮到界面，允许用户查看日志
                if hasattr(bpy.ops, 'blendermcp') and hasattr(bpy.ops.blendermcp, 'view_server_log'):
                    logger.info("用户可以通过'查看服务器日志'按钮查看详细错误信息")
    except Exception as e:
        logger.error(f"延迟启动服务器时出错: {e}", exc_info=True)
    
    return None  # 不再重复调用

if __name__ == "__main__":
    register()

# 导出公共API
__all__ = [ 'register', 'unregister']

# 版本信息
__version__ = '0.3.0' 