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

from ..common.errors import BlenderError, ParameterError, AuthError
from .api_spec import create_response, create_error, ERROR_CODES, APIRequest
from .security import SecurityValidator
from .auth import AuthManager, Permission

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
        self._loop = None
        
        # 初始化安全验证器和认证管理器
        self.security = SecurityValidator()
        self.auth = AuthManager()
        
        # 设置默认安全路径
        self.security.add_safe_path("./data")
        self.security.add_safe_path("./temp")
        
        # 设置默认用户和权限
        self._setup_default_auth()
        
    def _setup_default_auth(self):
        """设置默认用户和权限"""
        # 添加默认管理员用户
        self.auth.add_user("admin", "admin123", role="admin")
        
        # 添加默认普通用户
        self.auth.add_user("user", "user123", role="user")
        
        # 设置用户权限
        user_permissions = [
            Permission.CREATE_OBJECT,
            Permission.DELETE_OBJECT,
            Permission.MODIFY_OBJECT,
            Permission.SET_MATERIAL,
            Permission.GET_SCENE_INFO,
            Permission.GET_OBJECT_INFO,
            Permission.SET_LIGHT,
            Permission.SET_CAMERA
        ]
        
        for permission in user_permissions:
            self.auth.add_permission("user", permission)
            
    def register_handler(self, command: str, handler):
        """注册命令处理器"""
        self._command_handlers[command] = handler
            
    async def _handle_client(self, websocket):
        """Handle client connection"""
        session_id = None
        try:
            logger.info(f"客户端已连接: {websocket.remote_address}")
            
            async for message in websocket:
                try:
                    logger.debug(f"收到消息: {message}")
                    data = json.loads(message)
                    
                    # 验证消息格式
                    if not isinstance(data, dict):
                        raise ValueError("无效的消息格式")
                        
                    # 验证请求格式
                    if 'command' not in data:
                        raise ValueError("缺少command字段")
                    if 'params' not in data:
                        data['params'] = {}
                        
                    command = data['command']
                    params = data['params']
                    msg_id = data.get('id')
                    
                    # 处理认证命令
                    if command == 'authenticate':
                        try:
                            username = params.get('username')
                            password = params.get('password')
                            if not username or not password:
                                raise AuthError("缺少用户名或密码")
                                
                            session_id = self.auth.authenticate(username, password)
                            if not session_id:
                                raise AuthError("认证失败")
                                
                            response = create_response(
                                id=msg_id,
                                success=True,
                                result={'session_id': session_id}
                            )
                            await websocket.send(json.dumps(response))
                            continue
                            
                        except Exception as e:
                            logger.error(f"认证失败: {e}")
                            error = create_error(
                                ERROR_CODES['INVALID_PARAMETER'],
                                str(e)
                            )
                            response = create_response(
                                id=msg_id,
                                success=False,
                                error=error
                            )
                            await websocket.send(json.dumps(response))
                            continue
                            
                    # 验证会话
                    if not session_id:
                        error = create_error(
                            ERROR_CODES['INVALID_PARAMETER'],
                            "未认证的会话"
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                        await websocket.send(json.dumps(response))
                        continue
                        
                    if not self.auth.validate_session(session_id):
                        error = create_error(
                            ERROR_CODES['INVALID_PARAMETER'],
                            "会话已过期"
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                        await websocket.send(json.dumps(response))
                        continue
                        
                    # 验证权限
                    if not self.auth.check_permission(session_id, command):
                        error = create_error(
                            ERROR_CODES['INVALID_PARAMETER'],
                            "没有执行该命令的权限"
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                        await websocket.send(json.dumps(response))
                        continue
                        
                    # 安全验证
                    if not self.security.validate_command(command, params):
                        error = create_error(
                            ERROR_CODES['INVALID_PARAMETER'],
                            "命令验证失败"
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                        await websocket.send(json.dumps(response))
                        continue
                    
                    # 获取命令处理器
                    handler = self._command_handlers.get(command)
                    if not handler:
                        error = create_error(
                            ERROR_CODES['INVALID_PARAMETER'],
                            f"未知命令: {command}"
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                        await websocket.send(json.dumps(response))
                        continue
                        
                    # 执行命令
                    logger.info(f"执行命令: {command}")
                    try:
                        result = await handler(params)
                        response = create_response(
                            id=msg_id,
                            success=True,
                            result=result
                        )
                    except ParameterError as e:
                        error = create_error(
                            ERROR_CODES['INVALID_PARAMETER'],
                            str(e)
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                    except BlenderError as e:
                        error = create_error(
                            ERROR_CODES['OPERATION_FAILED'],
                            str(e)
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                    except asyncio.TimeoutError:
                        error = create_error(
                            ERROR_CODES['TIMEOUT'],
                            "操作超时"
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                    except Exception as e:
                        logger.error(f"执行命令时出错: {e}")
                        logger.error(f"错误堆栈: {traceback.format_exc()}")
                        error = create_error(
                            ERROR_CODES['OPERATION_FAILED'],
                            f"执行错误: {str(e)}"
                        )
                        response = create_response(
                            id=msg_id,
                            success=False,
                            error=error
                        )
                    
                    # 发送响应
                    logger.debug(f"发送响应: {response}")
                    await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError:
                    logger.error("JSON解析错误")
                    error = create_error(
                        ERROR_CODES['INVALID_PARAMETER'],
                        "无效的JSON格式"
                    )
                    response = create_response(
                        success=False,
                        error=error
                    )
                    await websocket.send(json.dumps(response))
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    error = create_error(
                        ERROR_CODES['OPERATION_FAILED'],
                        f"处理错误: {str(e)}"
                    )
                    response = create_response(
                        success=False,
                        error=error
                    )
                    await websocket.send(json.dumps(response))
                    
        except Exception as e:
            logger.error(f"处理客户端连接时出错: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
        finally:
            # 清理会话
            if session_id:
                self.auth.logout(session_id)
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
            
            # 启动会话清理任务
            asyncio.create_task(self._cleanup_sessions())
            
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
            
    async def _cleanup_sessions(self):
        """定期清理过期会话"""
        while self._running:
            try:
                self.auth.cleanup_sessions()
                await asyncio.sleep(300)  # 每5分钟清理一次
            except Exception as e:
                logger.error(f"清理会话时出错: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试
            
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