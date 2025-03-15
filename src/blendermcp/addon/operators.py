"""
BlenderMCP Operators

This module implements the operators for the BlenderMCP addon.
"""

import bpy
import logging
import threading
import asyncio
import weakref
from bpy.types import Operator
import traceback

logger = logging.getLogger(__name__)

# 全局服务器实例引用
_server_instance = None
_server_thread = None
_server_event_loop = None

class StartServerOperator(Operator):
    """Start BlenderMCP Server"""
    bl_idname = "blendermcp.start_server"
    bl_label = "Start Server"
    
    def execute(self, context):
        try:
            logger.info("启动服务器")
            
            # 检查服务器是否已经在运行
            global _server_instance, _server_thread, _server_event_loop
            if _server_instance is not None and _server_instance() is not None:
                logger.warning("服务器已经在运行")
                self.report({'WARNING'}, "服务器已经在运行")
                return {'CANCELLED'}
            
            # 动态导入服务器创建函数
            from ..server.server import create_server
            
            # 创建服务器实例
            server = create_server()
            _server_instance = weakref.ref(server)
            
            # 在新线程中运行服务器
            def run_server():
                try:
                    # 创建新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    global _server_event_loop
                    _server_event_loop = loop
                    
                    # 启动服务器
                    loop.run_until_complete(server.start())
                    loop.run_forever()
                except Exception as e:
                    logger.error(f"服务器运行出错: {e}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    context.scene.blendermcp.add_log(f"服务器运行出错: {e}", 'ERROR')
                finally:
                    # 清理事件循环
                    if not loop.is_closed():
                        loop.close()
                    _server_event_loop = None
                    
            # 创建并启动服务器线程
            thread = threading.Thread(target=run_server)
            thread.daemon = True
            thread.start()
            _server_thread = thread
            
            # 等待服务器启动
            import time
            for _ in range(10):  # 最多等待2秒
                if _server_event_loop is not None and server._running:
                    break
                time.sleep(0.2)
            
            if not server._running:
                raise RuntimeError("服务器启动超时")
            
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
            
            # 获取服务器实例
            global _server_instance, _server_thread, _server_event_loop
            if _server_instance is None:
                logger.warning("服务器实例不存在")
                context.scene.blendermcp.add_log("服务器实例不存在", 'WARNING')
                return {'CANCELLED'}
                
            server = _server_instance()
            if server is None:
                logger.warning("服务器实例已被回收")
                context.scene.blendermcp.add_log("服务器实例已被回收", 'WARNING')
                return {'CANCELLED'}
                
            # 停止服务器
            def stop_server():
                try:
                    # 获取事件循环
                    loop = _server_event_loop
                    if loop is None or loop.is_closed():
                        logger.warning("事件循环已关闭")
                        return
                        
                    # 停止服务器
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(server.stop())
                    )
                    
                    # 停止事件循环
                    loop.call_soon_threadsafe(loop.stop)
                except Exception as e:
                    logger.error(f"停止服务器时出错: {e}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    context.scene.blendermcp.add_log(f"停止服务器时出错: {e}", 'ERROR')
                    
            # 在新线程中停止服务器
            stop_thread = threading.Thread(target=stop_server)
            stop_thread.start()
            stop_thread.join()
            
            # 等待服务器线程结束
            if _server_thread is not None and _server_thread.is_alive():
                _server_thread.join(timeout=5.0)
            
            # 清理状态
            _server_instance = None
            _server_thread = None
            _server_event_loop = None
            
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
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 