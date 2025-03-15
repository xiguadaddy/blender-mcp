"""
BlenderMCP Server Core

This module contains the core server implementation.
"""

import asyncio
import json
import logging
import traceback
import threading
from typing import Dict, Any, Optional
import websockets
import time

from ..common.errors import BlenderError, ParameterError

logger = logging.getLogger(__name__)

class BlenderMCPServer:
    """BlenderMCP WebSocket server implementation"""
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        """Initialize the server
        
        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.server = None
        self._running = False
        self._command_handlers = {}
        self._startup_event = threading.Event()
        self._loop = None  # 保存事件循环引用
        
    def register_handler(self, command: str, handler):
        """注册命令处理器"""
        self._command_handlers[command] = handler
            
    async def _handle_client(self, websocket):
        """Handle client connection"""
        try:
            logger.info(f"客户端已连接: {websocket.remote_address}")
            
            async for message in websocket:
                try:
                    logger.debug(f"收到消息: {message}")
                    data = json.loads(message)
                    
                    # 验证消息格式
                    if not isinstance(data, dict):
                        raise ValueError("Invalid message format")
                        
                    command = data.get('command')
                    if not command:
                        raise ValueError("Missing command")
                        
                    # 获取命令处理器
                    handler = self._command_handlers.get(command)
                    if not handler:
                        raise ValueError(f"Unknown command: {command}")
                        
                    # 执行命令
                    logger.info(f"执行命令: {command}")
                    params = data.get('params', {})
                    result = await handler(params)
                    
                    # 发送响应
                    response = {
                        'id': data.get('id'),
                        'result': result
                    }
                    logger.debug(f"发送响应: {response}")
                    await websocket.send(json.dumps(response))
                    
                except Exception as e:
                    logger.error(f"处理命令时出错: {e}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    
                    # 发送错误响应
                    error_response = {
                        'id': data.get('id') if isinstance(data, dict) else None,
                        'error': {
                            'code': 500,
                            'message': str(e)
                        }
                    }
                    try:
                        await websocket.send(json.dumps(error_response))
                    except:
                        logger.error("发送错误响应失败")
                        
        except Exception as e:
            logger.error(f"处理客户端连接时出错: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
        finally:
            logger.info(f"客户端断开连接: {websocket.remote_address}")
            
    async def start(self):
        """Start the server"""
        if self._running:
            logger.warning("服务器已经在运行")
            return
            
        try:
            # 保存事件循环引用
            self._loop = asyncio.get_event_loop()
            
            # 启动服务器
            logger.info(f"启动服务器: {self.host}:{self.port}")
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            self._running = True
            self._startup_event.set()
            logger.info("服务器启动成功")
            
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            self._startup_event.set()  # 设置事件以避免阻塞
            raise
            
    async def stop(self):
        """Stop the server"""
        if not self._running:
            logger.warning("服务器未运行")
            return
            
        try:
            logger.info("停止服务器")
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.server = None
            self._running = False
            self._loop = None  # 清理事件循环引用
            logger.info("服务器已停止")
            
        except Exception as e:
            logger.error(f"停止服务器时出错: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise
            
    def wait_for_startup(self, timeout: float = 5.0) -> bool:
        """等待服务器启动
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 服务器是否成功启动
        """
        if self._startup_event.wait(timeout):
            return self._running
        return False
            
    def run(self):
        """Run the server in the current thread"""
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # 运行服务器
            loop.run_until_complete(self.start())
            loop.run_forever()
            
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        except Exception as e:
            logger.error(f"运行服务器时出错: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
        finally:
            # 停止服务器
            if self._running:
                loop.run_until_complete(self.stop())
            # 关闭事件循环
            loop.close() 