"""
BlenderMCP Operators

This module implements the operators for the BlenderMCP addon.
"""

import bpy
import logging
import threading
import subprocess
import os
import sys
import tempfile
from bpy.types import Operator
import traceback

logger = logging.getLogger(__name__)

# 全局服务器实例引用
_server_process = None
_server_thread = None
_server_running = False

class StartServerOperator(Operator):
    """Start BlenderMCP Server"""
    bl_idname = "blendermcp.start_server"
    bl_label = "Start Server"
    
    def execute(self, context):
        try:
            logger.info("启动服务器")
            
            # 检查服务器是否已经在运行
            global _server_process, _server_thread, _server_running
            if _server_running:
                logger.warning("服务器已经在运行")
                self.report({'WARNING'}, "服务器已经在运行")
                return {'CANCELLED'}
            
            # 获取Python可执行文件路径
            python_exe = "python" if sys.platform == "win32" else "python3"
            
            # 创建启动脚本
            script_content = """
import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入服务器模块
from blendermcp.server.server import create_server
import asyncio

# 创建并启动服务器
async def main():
    server = create_server()
    await server.start()
    await asyncio.Future()  # 永远运行

if __name__ == "__main__":
    asyncio.run(main())
"""
            
            # 创建临时脚本文件
            script_path = os.path.join(tempfile.gettempdir(), f"blendermcp_server_{os.getpid()}.py")
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # 启动服务器进程
            _server_process = subprocess.Popen(
                [python_exe, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 标记为运行中
            _server_running = True
            
            # 启动监控线程
            def monitor_process():
                global _server_process, _server_running
                
                # 等待进程结束
                _server_process.wait()
                
                # 进程已结束
                _server_running = False
                
                # 清理临时脚本
                try:
                    os.remove(script_path)
                except:
                    pass
                
                # 更新UI状态
                def update_ui():
                    try:
                        if bpy.context.scene is not None:
                            bpy.context.scene.blendermcp.add_log("服务器已停止", 'INFO')
                            bpy.context.scene.blendermcp.last_command = "stop_server"
                            bpy.context.scene.blendermcp.last_result = "Server stopped"
                            bpy.context.scene.blendermcp.last_result_success = True
                    except:
                        pass
                
                # 在主线程中更新UI
                bpy.app.timers.register(update_ui, first_interval=0.1)
            
            _server_thread = threading.Thread(target=monitor_process)
            _server_thread.daemon = True
            _server_thread.start()
            
            # 更新状态
            context.scene.blendermcp.add_log("服务器已启动", 'INFO')
            context.scene.blendermcp.last_command = "start_server"
            context.scene.blendermcp.last_result = "Server started"
            context.scene.blendermcp.last_result_success = True
            
            logger.info("服务器已启动")
            self.report({'INFO'}, "BlenderMCP服务器已启动")
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            context.scene.blendermcp.add_log(f"启动服务器失败: {e}", 'ERROR')
            context.scene.blendermcp.last_command = "start_server"
            context.scene.blendermcp.last_result = str(e)
            context.scene.blendermcp.last_result_success = False
            self.report({'ERROR'}, f"启动服务器失败: {str(e)}")
            return {'CANCELLED'}
            
class StopServerOperator(Operator):
    """Stop BlenderMCP Server"""
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop Server"
    
    def execute(self, context):
        try:
            logger.info("停止服务器")
            
            # 获取服务器进程
            global _server_process, _server_thread, _server_running
            if not _server_running or _server_process is None:
                logger.warning("服务器未运行")
                context.scene.blendermcp.add_log("服务器未运行", 'WARNING')
                return {'CANCELLED'}
            
            # 终止进程
            if sys.platform == "win32":
                # Windows上使用taskkill强制终止进程树
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(_server_process.pid)])
            else:
                # Unix系统上发送SIGTERM信号
                _server_process.terminate()
                
                # 等待进程结束
                _server_process.wait(timeout=5)
                
                # 如果进程仍在运行，强制终止
                if _server_process.poll() is None:
                    _server_process.kill()
            
            # 重置状态
            _server_running = False
            _server_process = None
            
            # 更新状态
            context.scene.blendermcp.add_log("服务器已停止", 'INFO')
            context.scene.blendermcp.last_command = "stop_server"
            context.scene.blendermcp.last_result = "Server stopped"
            context.scene.blendermcp.last_result_success = True
            
            logger.info("服务器已停止")
            self.report({'INFO'}, "BlenderMCP服务器已停止")
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"停止服务器失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            context.scene.blendermcp.add_log(f"停止服务器失败: {e}", 'ERROR')
            context.scene.blendermcp.last_command = "stop_server"
            context.scene.blendermcp.last_result = str(e)
            context.scene.blendermcp.last_result_success = False
            self.report({'ERROR'}, f"停止服务器失败: {str(e)}")
            return {'CANCELLED'}
            
class ClearLogOperator(Operator):
    """Clear BlenderMCP log"""
    bl_idname = "blendermcp.clear_log"
    bl_label = "Clear Log"
    
    def execute(self, context):
        try:
            context.scene.blendermcp.clear_logs()
            self.report({'INFO'}, "日志已清除")
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"清除日志失败: {e}")
            self.report({'ERROR'}, f"清除日志失败: {str(e)}")
            return {'CANCELLED'}

# 要注册的类
classes = (
    StartServerOperator,
    StopServerOperator,
    ClearLogOperator,
)

def register_operators():
    """注册所有操作符类"""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_operators():
    """注销所有操作符类"""
    # 确保服务器停止
    global _server_running, _server_process
    if _server_running and _server_process is not None:
        if sys.platform == "win32":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(_server_process.pid)])
        else:
            _server_process.terminate()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 