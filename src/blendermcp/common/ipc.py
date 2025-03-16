"""
进程间通信(IPC)模块

使用multiprocessing.Queue实现Blender插件与MCP服务器核心之间的通信
"""

import multiprocessing
import logging
import json
import time
import uuid
import threading
from typing import Dict, Any, Optional, Tuple, Callable

# 设置日志
logger = logging.getLogger("BlenderMCP.IPC")

# 全局消息队列
REQUEST_QUEUE: Optional[multiprocessing.Queue] = None
RESPONSE_QUEUE: Optional[multiprocessing.Queue] = None

# 响应等待超时时间(秒)
RESPONSE_TIMEOUT = 30.0

# 正在等待的请求
# 格式: {request_id: (event, response_container)}
waiting_requests: Dict[str, Tuple[threading.Event, Dict[str, Any]]] = {}

def init_queues():
    """初始化消息队列，在服务器进程和Blender进程都需要调用"""
    global REQUEST_QUEUE, RESPONSE_QUEUE
    
    if REQUEST_QUEUE is None:
        REQUEST_QUEUE = multiprocessing.Queue()
    if RESPONSE_QUEUE is None:
        RESPONSE_QUEUE = multiprocessing.Queue()
    
    logger.info("IPC消息队列已初始化")

def cleanup_queues():
    """清理消息队列"""
    global REQUEST_QUEUE, RESPONSE_QUEUE
    
    # 清空队列
    if REQUEST_QUEUE:
        while not REQUEST_QUEUE.empty():
            try:
                REQUEST_QUEUE.get_nowait()
            except:
                pass
    
    if RESPONSE_QUEUE:
        while not RESPONSE_QUEUE.empty():
            try:
                RESPONSE_QUEUE.get_nowait()
            except:
                pass
    
    # 重置等待中的请求
    waiting_requests.clear()
    
    logger.info("IPC消息队列已清理")

# ----------- 服务器端API -----------

def start_response_listener(callback: Callable[[Dict[str, Any]], None]):
    """
    启动响应监听器线程，在服务器端调用
    
    Args:
        callback: 收到响应时的回调函数
    """
    def _listener_thread():
        while True:
            try:
                if RESPONSE_QUEUE and not RESPONSE_QUEUE.empty():
                    response = RESPONSE_QUEUE.get()
                    callback(response)
            except Exception as e:
                logger.error(f"响应监听器错误: {str(e)}")
            time.sleep(0.01)  # 避免CPU高占用
    
    thread = threading.Thread(target=_listener_thread, daemon=True)
    thread.start()
    logger.info("服务器端响应监听器已启动")
    return thread

def send_request_to_blender(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    发送请求到Blender并等待响应，在服务器端调用
    
    Args:
        request: 请求数据
        
    Returns:
        dict: 响应数据
    """
    # 确保请求有唯一ID
    if "id" not in request:
        request["id"] = str(uuid.uuid4())
    
    request_id = request["id"]
    
    # 创建等待事件和响应容器
    event = threading.Event()
    response_container = {}
    waiting_requests[request_id] = (event, response_container)
    
    # 发送请求
    REQUEST_QUEUE.put(request)
    logger.debug(f"已发送请求到Blender: {request}")
    
    # 等待响应
    if not event.wait(timeout=RESPONSE_TIMEOUT):
        logger.error(f"请求超时: {request_id}")
        del waiting_requests[request_id]
        return {"status": "error", "message": "Request timeout"}
    
    # 获取响应
    response = response_container.get("response", {})
    del waiting_requests[request_id]
    
    return response

def handle_blender_response(response: Dict[str, Any]):
    """
    处理来自Blender的响应，在服务器端调用
    
    Args:
        response: 响应数据
    """
    if "id" not in response:
        logger.error(f"收到无ID的响应: {response}")
        return
    
    request_id = response["id"]
    if request_id in waiting_requests:
        event, container = waiting_requests[request_id]
        container["response"] = response
        event.set()
        logger.debug(f"已收到响应: {response}")
    else:
        logger.warning(f"收到未知请求的响应: {request_id}")

# ----------- Blender端API -----------

def start_request_processor(processor: Callable[[Dict[str, Any]], Dict[str, Any]]):
    """
    启动请求处理器线程，在Blender端调用
    
    Args:
        processor: 处理请求的函数，接收请求返回响应
    """
    def _processor_thread():
        while True:
            try:
                if REQUEST_QUEUE and not REQUEST_QUEUE.empty():
                    request = REQUEST_QUEUE.get()
                    logger.debug(f"收到服务器请求: {request}")
                    
                    # 处理请求
                    response = processor(request)
                    
                    # 确保响应包含请求ID
                    if "id" in request and "id" not in response:
                        response["id"] = request["id"]
                    
                    # 发送响应
                    RESPONSE_QUEUE.put(response)
                    logger.debug(f"已发送响应: {response}")
            except Exception as e:
                logger.error(f"处理请求错误: {str(e)}")
                # 发送错误响应
                if "id" in request:
                    error_response = {
                        "id": request["id"],
                        "status": "error",
                        "message": str(e)
                    }
                    RESPONSE_QUEUE.put(error_response)
            time.sleep(0.01)  # 避免CPU高占用
    
    thread = threading.Thread(target=_processor_thread, daemon=True)
    thread.start()
    logger.info("Blender端请求处理器已启动")
    return thread 