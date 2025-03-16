"""
Blender中处理外部请求的监听器组件。

此模块实现了一个简单的WebSocket客户端，连接到MCP服务器，
并处理来自服务器的请求。
"""

import bpy
import time
import threading
import json
import traceback
import logging
import os
import sys
import subprocess
from pathlib import Path
from . import globals
from . import executor
from . import preferences as prefs
from ..common import ipc

# 日志配置
logger = logging.getLogger(__name__)

# 全局变量
_websocket_client = None
_processor_thread = None
_running = False

# 初始化IPC队列
ipc.init_queues()

def _find_python_executable():
    """查找可用的Python解释器路径"""
    # 首先尝试使用系统默认的Python
    if sys.executable and not sys.executable.endswith('blender.exe') and not sys.executable.endswith('blender'):
        return sys.executable
    
    # 在Windows上尝试查找Python
    if os.name == 'nt':
        for version in ['3.10', '3.9', '3.8', '3.7', '3']:
            try:
                # 从注册表中查找Python安装路径
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"SOFTWARE\\Python\\PythonCore\\{version}\\InstallPath")
                value, _ = winreg.QueryValueEx(key, "")
                python_path = os.path.join(value, "python.exe")
                if os.path.exists(python_path):
                    return python_path
            except:
                pass
            
            # 尝试常见安装路径
            paths = [
                f"C:\\Python{version.replace('.', '')}\\python.exe",
                f"C:\\Program Files\\Python{version.replace('.', '')}\\python.exe",
                f"C:\\Program Files (x86)\\Python{version.replace('.', '')}\\python.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
    
    # Unix/Linux/Mac上尝试查找Python
    else:
        for cmd in ['python3', 'python']:
            try:
                path = subprocess.check_output(['which', cmd], text=True).strip()
                if path and os.path.exists(path):
                    return path
            except:
                pass
    
    return None

def start():
    """启动请求监听器和WebSocket客户端"""
    global _running, _processor_thread, _websocket_client
    
    if _running:
        logger.info("BlenderMCP监听器已经在运行中")
        return

    try:
        # 获取WebSocket连接地址和端口
        addon_prefs = prefs.get_addon_preferences(bpy.context)
        ws_host = addon_prefs.websocket_host
        ws_port = addon_prefs.websocket_port
        
        # 使用server_operators启动MCP服务器
        from . import server_operators
        success, message = server_operators.start_server(host=ws_host, port=ws_port, debug=True)
        
        if not success:
            logger.error(f"启动MCP服务器失败: {message}")
            return False
            
        logger.info(f"MCP服务器启动成功: {message}")
    
        # 启动请求处理线程
        _running = True
        _processor_thread = threading.Thread(target=_process_requests, daemon=True)
        _processor_thread.start()
        
        # 启动WebSocket客户端
        client_thread = threading.Thread(target=_start_websocket_client, args=(ws_host, ws_port), daemon=True)
        client_thread.start()
        
        logger.info("BlenderMCP监听器已启动")
        return True
        
    except Exception as e:
        _running = False
        logger.error(f"启动BlenderMCP监听器时出错: {e}")
        traceback.print_exc()
        return False

def stop():
    """停止请求监听器和WebSocket客户端"""
    global _running, _websocket_client
    
    if not _running:
        return
    
    _running = False
    
    # 关闭WebSocket连接
    if _websocket_client:
        try:
            _websocket_client.close()
            _websocket_client = None
        except:
            pass
    
    # 终止MCP服务器进程
    if globals.mcp_server_process:
        try:
            globals.mcp_server_process.terminate()
            globals.mcp_server_process = None
        except:
            pass
    
    logger.info("BlenderMCP监听器已停止")

def _process_requests():
    """从请求队列中处理请求"""
    global _running
    
    while _running:
        try:
            # 从队列中获取请求
            if not ipc.REQUEST_QUEUE.empty():
                request = ipc.REQUEST_QUEUE.get(block=False)
                if request:
                    # 处理请求
                    try:
                        result = executor.process_request(request)
                        # 将结果放入响应队列
                        if 'id' in request:
                            response = {
                                'id': request['id'],
                                'result': result,
                                'error': None
                            }
                            ipc.RESPONSE_QUEUE.put(response)
                    except Exception as e:
                        # 处理请求时出错
                        if 'id' in request:
                            response = {
                                'id': request['id'],
                                'result': None,
                                'error': {
                                    'message': str(e),
                                    'traceback': traceback.format_exc()
                                }
                            }
                            ipc.RESPONSE_QUEUE.put(response)
                        logger.error(f"处理请求时出错: {e}")
                        traceback.print_exc()
            
            # 休眠一小段时间，避免CPU占用过高
            time.sleep(0.01)
            
        except Exception as e:
            logger.error(f"请求处理线程中出错: {e}")
            traceback.print_exc()
            time.sleep(1)  # 出错后等待一段时间再继续

def _start_websocket_client(host, port):
    """启动WebSocket客户端，连接到MCP服务器"""
    global _websocket_client, _running
    
    # 构建WebSocket URL
    ws_url = f"ws://{host}:{port}"
    logger.info(f"正在连接到MCP服务器: {ws_url}")
    
    retry_count = 0
    max_retries = 5
    
    while _running and retry_count < max_retries:
        try:
            # 尝试导入websocket-client库
            try:
                import websocket
            except ImportError:
                # 如果没有安装websocket-client库，设置路径并再次尝试
                logger.info("没有找到websocket-client库，正在尝试使用lib目录...")
                lib_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
                if os.path.exists(lib_dir) and lib_dir not in sys.path:
                    sys.path.insert(0, lib_dir)
                    try:
                        import websocket
                        logger.info("在lib目录找到websocket-client库")
                    except ImportError:
                        # 仍然无法导入，回到上层__init__.py中的ensure_dependencies
                        logger.error("未找到websocket-client库，请确保插件已正确安装")
                        return False
            
            # 创建一个WebSocketApp
            logger.info("创建WebSocketApp连接...")
            _websocket_client = websocket.WebSocketApp(
                ws_url,
                on_open=_handle_websocket_open,
                on_message=_handle_websocket_message,
                on_error=_handle_websocket_error,
                on_close=_handle_websocket_close
            )
            
            # 在单独的线程中运行WebSocket客户端
            websocket_thread = threading.Thread(target=_websocket_client.run_forever)
            websocket_thread.daemon = True
            websocket_thread.start()
            
            # 等待一段时间，确保连接成功
            start_time = time.time()
            while time.time() - start_time < 5:  # 5秒超时
                if _websocket_client.sock and _websocket_client.sock.connected:
                    logger.info("WebSocket连接成功")
                    return True
                time.sleep(0.1)
            
            # 连接超时
            logger.warning("WebSocket连接超时，正在重试...")
            retry_count += 1
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {str(e)}")
            retry_count += 1
            time.sleep(1)  # 等待1秒后重试
    
    if retry_count >= max_retries:
        logger.error(f"WebSocket连接失败，已达到最大重试次数: {max_retries}")
    
    return False

def _handle_websocket_open(ws):
    """WebSocket连接打开时的处理函数"""
    logger.info("已连接到MCP服务器")
    
    # 注册客户端
    try:
        register_message = {
            'type': 'register',
            'role': 'blender',
            'version': globals.VERSION
        }
        ws.send(json.dumps(register_message))
    except Exception as e:
        logger.error(f"注册客户端时出错: {e}")
        traceback.print_exc()

def _handle_websocket_message(ws, message):
    """处理WebSocket接收到的消息"""
    try:
        # 解析消息
        data = json.loads(message)
        
        # 根据消息类型处理
        if data['type'] == 'request':
            # 将请求放入队列
            ipc.REQUEST_QUEUE.put(data['request'])
        elif data['type'] == 'ping':
            # 响应ping消息
            pong_message = {
                'type': 'pong',
                'timestamp': data.get('timestamp', time.time())
            }
            ws.send(json.dumps(pong_message))
        
        # 检查响应队列
        while not ipc.RESPONSE_QUEUE.empty():
            try:
                response = ipc.RESPONSE_QUEUE.get(block=False)
                if response:
                    response_message = {
                        'type': 'response',
                        'response': response
                    }
                    ws.send(json.dumps(response_message))
            except Exception as e:
                logger.error(f"发送响应时出错: {e}")
                break
                
    except Exception as e:
        logger.error(f"处理WebSocket消息时出错: {e}")
        traceback.print_exc()

def _handle_websocket_error(ws, error):
    """处理WebSocket错误"""
    logger.error(f"WebSocket错误: {error}")

def _handle_websocket_close(ws, close_status_code, close_msg):
    """处理WebSocket连接关闭"""
    logger.info(f"WebSocket连接已关闭: 状态码={close_status_code}, 消息={close_msg}")

def is_running():
    """检查监听器是否正在运行
    
    Returns:
        bool: 监听器是否正在运行
    """
    global _running
    return _running
