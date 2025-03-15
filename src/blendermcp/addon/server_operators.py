"""
BlenderMCP服务器操作模块

该模块提供了启动和停止MCP服务器的功能，支持WebSocket和标准输入/输出模式。
"""

import os
import sys
import subprocess
import threading
import logging
import tempfile
import time
import bpy
from pathlib import Path

# 配置日志
log_file = os.path.join(tempfile.gettempdir(), "blendermcp_addon.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局变量
server_process = None
server_thread = None
server_url = None

def get_python_executable():
    """获取Python可执行文件路径"""
    # 尝试使用系统Python
    if sys.platform == "win32":
        python_exe = "python"
    else:
        python_exe = "python3"
    
    return python_exe

def get_script_path():
    """获取MCP服务器脚本路径"""
    # 获取当前插件目录
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建脚本路径（假设脚本位于src/blendermcp/scripts目录）
    scripts_dir = os.path.join(os.path.dirname(addon_dir), "scripts")
    script_path = os.path.join(scripts_dir, "run_mcp_server.py")
    
    logger.info(f"MCP服务器脚本路径: {script_path}")
    return script_path

def start_mcp_server_process(mode="websocket", host="localhost", port=9876):
    """启动MCP服务器进程"""
    global server_process, server_url
    
    if server_process is not None:
        logger.warning("MCP服务器已在运行，无法再次启动")
        return False
    
    try:
        # 获取Python可执行文件和脚本路径
        python_exe = get_python_executable()
        script_path = get_script_path()
        
        # 构建命令
        if mode.lower() == "websocket":
            cmd = [python_exe, script_path, "--mode", "websocket", "--host", host, "--port", str(port)]
            server_url = f"ws://{host}:{port}"
        else:
            cmd = [python_exe, script_path, "--mode", "stdio"]
            server_url = None
        
        logger.info(f"启动MCP服务器: {' '.join(cmd)}")
        
        # 启动进程
        server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        
        # 等待服务器启动
        time.sleep(2)
        
        # 检查进程是否仍在运行
        if server_process.poll() is not None:
            logger.error(f"MCP服务器启动失败，退出码: {server_process.returncode}")
            stderr_output = server_process.stderr.read()
            logger.error(f"错误输出: {stderr_output}")
            server_process = None
            return False
        
        logger.info("MCP服务器已成功启动")
        return True
        
    except Exception as e:
        logger.error(f"启动MCP服务器时出错: {str(e)}", exc_info=True)
        server_process = None
        return False

def stop_mcp_server_process():
    """停止MCP服务器进程"""
    global server_process, server_url
    
    if server_process is None:
        logger.warning("MCP服务器未运行，无法停止")
        return False
    
    try:
        logger.info("正在停止MCP服务器...")
        
        # 终止进程
        if sys.platform == "win32":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(server_process.pid)])
        else:
            server_process.terminate()
            server_process.wait(timeout=5)
            if server_process.poll() is None:
                server_process.kill()
        
        # 清理
        server_process = None
        server_url = None
        
        logger.info("MCP服务器已停止")
        return True
        
    except Exception as e:
        logger.error(f"停止MCP服务器时出错: {str(e)}", exc_info=True)
        return False

def monitor_server_process():
    """监控服务器进程"""
    global server_process
    
    while server_process is not None and server_process.poll() is None:
        # 检查是否有错误输出
        stderr_line = server_process.stderr.readline()
        if stderr_line:
            logger.error(f"服务器错误输出: {stderr_line.strip()}")
        
        # 检查是否有标准输出
        stdout_line = server_process.stdout.readline()
        if stdout_line:
            logger.info(f"服务器输出: {stdout_line.strip()}")
        
        time.sleep(0.1)
    
    # 进程已结束
    if server_process is not None:
        exit_code = server_process.returncode
        logger.info(f"MCP服务器进程已结束，退出码: {exit_code}")
        server_process = None

def start_server_thread():
    """在单独的线程中启动服务器监控"""
    global server_thread
    
    if server_thread is not None and server_thread.is_alive():
        logger.warning("服务器监控线程已在运行")
        return
    
    server_thread = threading.Thread(target=monitor_server_process)
    server_thread.daemon = True
    server_thread.start()
    logger.info("服务器监控线程已启动")

def is_server_running():
    """检查服务器是否正在运行"""
    return server_process is not None and server_process.poll() is None

def get_server_url():
    """获取服务器URL"""
    return server_url

class MCP_OT_StartServer(bpy.types.Operator):
    """启动MCP服务器"""
    bl_idname = "mcp.start_server"
    bl_label = "启动MCP服务器"
    bl_description = "启动MCP服务器，支持WebSocket和标准输入/输出模式"
    
    def execute(self, context):
        preferences = context.preferences.addons["blendermcp"].preferences
        mode = preferences.server_mode.lower()
        host = preferences.server_host
        port = preferences.server_port
        
        if is_server_running():
            self.report({'WARNING'}, "MCP服务器已在运行")
            return {'CANCELLED'}
        
        if start_mcp_server_process(mode, host, port):
            start_server_thread()
            self.report({'INFO'}, f"MCP服务器已启动 ({mode})")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "启动MCP服务器失败")
            return {'CANCELLED'}

class MCP_OT_StopServer(bpy.types.Operator):
    """停止MCP服务器"""
    bl_idname = "mcp.stop_server"
    bl_label = "停止MCP服务器"
    bl_description = "停止当前运行的MCP服务器"
    
    def execute(self, context):
        if not is_server_running():
            self.report({'WARNING'}, "MCP服务器未运行")
            return {'CANCELLED'}
        
        if stop_mcp_server_process():
            self.report({'INFO'}, "MCP服务器已停止")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "停止MCP服务器失败")
            return {'CANCELLED'}

class MCP_OT_CopyWebSocketURL(bpy.types.Operator):
    """复制WebSocket URL到剪贴板"""
    bl_idname = "mcp.copy_websocket_url"
    bl_label = "复制WebSocket URL"
    bl_description = "复制WebSocket URL到剪贴板"
    
    def execute(self, context):
        url = get_server_url()
        
        if not url:
            self.report({'ERROR'}, "WebSocket URL不可用")
            return {'CANCELLED'}
        
        context.window_manager.clipboard = url
        self.report({'INFO'}, f"已复制URL: {url}")
        return {'FINISHED'}

# 注册和注销
def register():
    bpy.utils.register_class(MCP_OT_StartServer)
    bpy.utils.register_class(MCP_OT_StopServer)
    bpy.utils.register_class(MCP_OT_CopyWebSocketURL)

def unregister():
    bpy.utils.unregister_class(MCP_OT_CopyWebSocketURL)
    bpy.utils.unregister_class(MCP_OT_StopServer)
    bpy.utils.unregister_class(MCP_OT_StartServer)
    
    # 确保服务器在插件卸载时停止
    if is_server_running():
        stop_mcp_server_process() 
