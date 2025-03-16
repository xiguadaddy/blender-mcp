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
from pathlib import Path

# 尝试导入bpy模块
try:
    import bpy
    from bpy.types import Operator
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    # 在没有bpy模块时创建一个空的Operator类作为替代
    class Operator:
        """替代Blender的Operator类，用于服务器独立运行时"""
        bl_idname = ""
        bl_label = ""
        bl_description = ""
        bl_options = {'REGISTER'}
        
        def execute(self, context):
            return {'FINISHED'}
        
        def report(self, type, message):
            print(f"Report [{type}]: {message}")

# 日志配置
logger = logging.getLogger("BlenderMCP.Server")

# 全局变量
SERVER_PROCESS = None
SERVER_LOG_FILE = os.path.join(tempfile.gettempdir(), "blendermcp_server_output.log")

def get_addon_path():
    """获取插件路径"""
    if HAS_BPY:
        # 在Blender中运行时
        # 获取所有脚本路径
        script_paths = bpy.utils.script_paths()
        
        # 遍历所有脚本路径，查找addons目录下的blendermcp
        for script_path in script_paths:
            addon_path = os.path.join(script_path, "addons", "blendermcp")
            if os.path.exists(addon_path):
                return addon_path
        
        # 如果上面的方法找不到，尝试从当前文件路径推断
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 直接运行时
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_script_path():
    """获取服务器脚本路径"""
    addon_path = get_addon_path()
    
    # 首先尝试简化版服务器脚本
    paths = [
        os.path.join(addon_path, "server", "run_mcp_server_simple.py"),
        os.path.join(addon_path, "server", "run_mcp_server.py"),
        os.path.join(addon_path, "scripts", "start_mcp_service.py")
    ]
    
    for path in paths:
        if os.path.exists(path):
            logger.info(f"使用服务器脚本: {path}")
            return path
    
    # 如果未找到，记录可用路径并抛出异常
    logger.error(f"未找到服务器脚本。已检查路径: {paths}")
    raise FileNotFoundError(f"未找到服务器脚本。已检查路径: {paths}")

def start_server(host="127.0.0.1", port=9876, debug=False):
    """启动MCP服务器进程
    
    Args:
        host: 服务器主机地址
        port: 服务器端口
        debug: 是否启用调试模式
        
    Returns:
        tuple: (是否成功, 消息)
    """
    global SERVER_PROCESS
    
    try:
        # 如果已有进程在运行，先停止
        if SERVER_PROCESS is not None:
            success, message = stop_server()
            if not success:
                logger.warning(f"停止旧服务器失败: {message}")
        
        # 获取脚本路径
        try:
            script_path = get_script_path()
        except FileNotFoundError as e:
            return False, str(e)
        
        # 确保日志文件目录存在
        log_dir = os.path.dirname(SERVER_LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建或清空日志文件
        with open(SERVER_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== BlenderMCP服务器日志 - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"正在启动服务器：{host}:{port}\n")
            f.write(f"脚本路径：{script_path}\n\n")
        
        # 构建命令
        python_exe = sys.executable
        cmd = [
            python_exe, 
            script_path, 
            "--host", host, 
            "--port", str(port)
        ]
        
        if debug:
            cmd.append("--debug")
        
        # 设置环境变量
        env = os.environ.copy()
        addon_path = get_addon_path()
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{addon_path}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = addon_path
            
        # 记录启动命令
        logger.info(f"启动服务器命令: {' '.join(cmd)}")
        logger.info(f"PYTHONPATH: {env['PYTHONPATH']}")
        with open(SERVER_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"启动命令: {' '.join(cmd)}\n")
            f.write(f"PYTHONPATH: {env['PYTHONPATH']}\n")
        
        # 重定向输出到日志文件
        log_file = open(SERVER_LOG_FILE, 'a', encoding='utf-8')
        
        # 启动进程
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            
        SERVER_PROCESS = subprocess.Popen(
            cmd,
            env=env,
            stdout=log_file,
            stderr=log_file,
            text=True,
            creationflags=creationflags
        )
        
        # 等待一小段时间，检查进程是否成功启动
        time.sleep(1)
        if SERVER_PROCESS.poll() is not None:
            # 进程已退出，读取日志文件获取错误信息
            log_file.close()
            with open(SERVER_LOG_FILE, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 进程退出代码
            exit_code = SERVER_PROCESS.returncode
            error_msg = f"服务器进程退出，代码: {exit_code}\n"
            error_msg += f"日志内容:\n{log_content}"
            
            SERVER_PROCESS = None
            logger.error(error_msg)
            return False, f"服务器启动失败，退出代码: {exit_code}"
        
        logger.info(f"服务器进程已启动，PID: {SERVER_PROCESS.pid}")
        return True, f"服务器已启动，PID: {SERVER_PROCESS.pid}"
        
    except Exception as e:
        logger.error(f"启动服务器时出错: {e}", exc_info=True)
        return False, f"启动服务器时出错: {e}"

def stop_server():
    """停止MCP服务器进程
    
    Returns:
        tuple: (是否成功, 消息)
    """
    global SERVER_PROCESS
    
    if SERVER_PROCESS is not None:
        try:
            # 在Windows上，正常终止进程
            if sys.platform == "win32":
                import ctypes
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, SERVER_PROCESS.pid)
                ctypes.windll.kernel32.TerminateProcess(handle, 0)
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                # 在其他平台上，发送终止信号
                SERVER_PROCESS.terminate()
                
            # 等待进程结束
            SERVER_PROCESS.wait(timeout=5)
            
            logger.info(f"服务器进程已停止，PID: {SERVER_PROCESS.pid}")
            SERVER_PROCESS = None
            return True, "服务器已停止"
            
        except Exception as e:
            logger.error(f"停止服务器时出错: {e}")
            SERVER_PROCESS = None
            return False, f"停止服务器时出错: {e}"
    else:
        logger.info("没有运行的服务器进程")
        return True, "没有运行的服务器进程"

def is_server_running():
    """检查服务器是否正在运行
    
    Returns:
        bool: 服务器是否运行中
    """
    global SERVER_PROCESS
    
    if SERVER_PROCESS is None:
        return False
        
    # 检查进程是否存活
    return SERVER_PROCESS.poll() is None

def get_server_log():
    """获取服务器日志内容
    
    Returns:
        str: 日志内容
    """
    if not os.path.exists(SERVER_LOG_FILE):
        return "服务器日志文件不存在"
        
    try:
        with open(SERVER_LOG_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"读取日志文件失败: {e}"

def get_server_mode():
    """获取服务器模式"""
    if not is_server_running():
        return "unknown"
    return "websocket"  # 目前仅支持websocket模式

def get_server_host():
    """获取服务器主机地址"""
    return "localhost"  # 默认值，可以从环境或配置获取

def get_server_port():
    """获取服务器端口"""
    return 9876  # 默认值，可以从环境或配置获取

def get_server_status():
    """获取服务器状态信息"""
    running = is_server_running()
    status = {
        "is_running": running,
        "mode": get_server_mode(),
        "host": get_server_host(),
        "port": get_server_port()
    }
    
    if running and SERVER_PROCESS:
        status["pid"] = SERVER_PROCESS.pid
        status["uptime"] = "00:00:00"  # 简化实现
        status["connections"] = 0  # 简化实现
        status["requests"] = 0  # 简化实现
        
    return status

# Blender操作类：启动服务器
class BLENDERMCP_OT_StartServer(Operator):
    """启动BlenderMCP服务器"""
    bl_idname = "blendermcp.start_server"
    bl_label = "启动服务器"
    bl_description = "启动BlenderMCP服务器进程"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        if HAS_BPY:
            # 获取插件偏好设置
            from . import preferences
            prefs = preferences.get_addon_preferences(context)
            
            # 获取WebSocket主机和端口
            ws_host = prefs.websocket_host
            ws_port = prefs.websocket_port
            
            # 启动服务器
            success, message = start_server(host=ws_host, port=ws_port, debug=True)
        else:
            # 直接启动服务器（用于测试）
            success, message = start_server(debug=True)
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
            
        return {'FINISHED'}

# Blender操作类：停止服务器
class BLENDERMCP_OT_StopServer(Operator):
    """停止BlenderMCP服务器"""
    bl_idname = "blendermcp.stop_server"
    bl_label = "停止服务器"
    bl_description = "停止BlenderMCP服务器进程"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        # 停止服务器
        success, message = stop_server()
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
            
        return {'FINISHED'}

# Blender操作类：查看服务器日志
class BLENDERMCP_OT_ViewServerLog(Operator):
    """查看服务器日志"""
    bl_idname = "blendermcp.view_server_log"
    bl_label = "查看服务器日志"
    bl_description = "打开服务器日志文件"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        if os.path.exists(SERVER_LOG_FILE):
            # 在操作系统中打开日志文件
            if sys.platform == "win32":
                os.startfile(SERVER_LOG_FILE)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", SERVER_LOG_FILE])
            else:  # Linux
                subprocess.call(["xdg-open", SERVER_LOG_FILE])
                
            self.report({'INFO'}, f"已打开服务器日志文件: {SERVER_LOG_FILE}")
        else:
            self.report({'ERROR'}, f"服务器日志文件不存在: {SERVER_LOG_FILE}")
            
        return {'FINISHED'}

# Blender操作类：复制服务器日志
class BLENDERMCP_OT_CopyServerLog(Operator):
    """复制服务器日志到剪贴板"""
    bl_idname = "blendermcp.copy_server_log"
    bl_label = "复制日志"
    bl_description = "复制服务器日志到剪贴板"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        log_content = get_server_log()
        
        if HAS_BPY:
            context.window_manager.clipboard = log_content
            self.report({'INFO'}, "服务器日志已复制到剪贴板")
        else:
            print(log_content)
            self.report({'INFO'}, "服务器日志已打印到控制台")
            
        return {'FINISHED'}

# Blender操作类：复制WebSocket URL
class BLENDERMCP_OT_CopyWebSocketURL(Operator):
    """复制WebSocket URL到剪贴板"""
    bl_idname = "blendermcp.copy_websocket_url"
    bl_label = "复制WebSocket URL"
    bl_description = "复制WebSocket URL到剪贴板"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        if is_server_running():
            host = get_server_host()
            port = get_server_port()
            url = f"ws://{host}:{port}"
            
            if HAS_BPY:
                context.window_manager.clipboard = url
                self.report({'INFO'}, f"已复制URL: {url}")
            else:
                print(f"WebSocket URL: {url}")
                self.report({'INFO'}, f"URL已打印到控制台: {url}")
        else:
            self.report({'ERROR'}, "服务器未运行")
            
        return {'FINISHED'}

# 注册类
classes = (
    BLENDERMCP_OT_StartServer,
    BLENDERMCP_OT_StopServer,
    BLENDERMCP_OT_ViewServerLog,
    BLENDERMCP_OT_CopyServerLog,
    BLENDERMCP_OT_CopyWebSocketURL,
)

def register():
    """注册操作类"""
    if HAS_BPY:
        for cls in classes:
            bpy.utils.register_class(cls)

def unregister():
    """注销操作类"""
    if HAS_BPY:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls) 
