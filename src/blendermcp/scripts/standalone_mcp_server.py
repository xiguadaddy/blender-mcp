#!/usr/bin/env python
"""
独立的MCP服务器脚本

该脚本包含一个简化版的MCP服务器实现，用于测试目的。
"""

import asyncio
import json
import logging
import sys
import signal
import os
import tempfile
from typing import Dict, List, Any, Optional, Union, Set
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

# 配置日志
log_file = os.path.join(tempfile.gettempdir(), 'standalone_mcp_server.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_file,
    filemode='a'
)

logger = logging.getLogger(__name__)

class MCPAdapter:
    """MCP适配器类"""
    
    def __init__(self):
        """初始化MCP适配器"""
        self.tools = {}
        self.prompts = {}
        
    def register_tool(self, name: str, handler: callable) -> None:
        """注册工具
        
        Args:
            name: 工具名称
            handler: 工具处理函数
        """
        self.tools[name] = handler
        
    def register_prompt(self, id: str, prompt: Dict[str, Any]) -> None:
        """注册提示
        
        Args:
            id: 提示ID
            prompt: 提示内容
        """
        self.prompts[id] = prompt
        
    async def handle_message(self, message: str) -> str:
        """处理MCP消息
        
        Args:
            message: JSON-RPC消息
            
        Returns:
            JSON-RPC响应
        """
        try:
            request = json.loads(message)
            
            # 检查是否是有效的JSON-RPC请求
            if not isinstance(request, dict) or request.get('jsonrpc') != '2.0':
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32600,
                        "message": "无效的请求"
                    }
                })
                
            method = request.get('method')
            params = request.get('params', {})
            request_id = request.get('id')
            
            # 处理方法
            if method == 'initialize':
                return self._handle_initialize(request_id)
            elif method == 'shutdown':
                return self._handle_shutdown(request_id)
            elif method == 'listTools':
                return self._handle_list_tools(request_id)
            elif method == 'callTool':
                return await self._handle_call_tool(request_id, params)
            elif method == 'getPrompt':
                return self._handle_get_prompt(request_id, params)
            else:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"方法不存在: {method}"
                    }
                })
                
        except json.JSONDecodeError:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "解析错误"
                }
            })
            
        except Exception as e:
            logger.exception(f"处理消息时出错: {e}")
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"内部错误: {str(e)}"
                }
            })
            
    def _handle_initialize(self, request_id: Union[str, int, None]) -> str:
        """处理初始化请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            JSON-RPC响应
        """
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "name": "BlenderMCP",
                "version": "0.1.0",
                "status": "ok"
            }
        })
        
    def _handle_shutdown(self, request_id: Union[str, int, None]) -> str:
        """处理关闭请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            JSON-RPC响应
        """
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "status": "ok"
            }
        })
        
    def _handle_list_tools(self, request_id: Union[str, int, None]) -> str:
        """处理工具列表请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            JSON-RPC响应
        """
        tools = []
        
        for name, handler in self.tools.items():
            tool = {
                "name": name,
                "description": getattr(handler, "__doc__", ""),
                "inputSchema": {}
            }
            tools.append(tool)
            
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        })
        
    async def _handle_call_tool(self, request_id: Union[str, int, None], params: Dict[str, Any]) -> str:
        """处理工具调用请求
        
        Args:
            request_id: 请求ID
            params: 请求参数
            
        Returns:
            JSON-RPC响应
        """
        tool_name = params.get('name')
        tool_params = params.get('params', {})
        
        if not tool_name:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "缺少工具名称"
                }
            })
            
        handler = self.tools.get(tool_name)
        if not handler:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"工具不存在: {tool_name}"
                }
            })
            
        try:
            # 调用工具处理函数
            result = await handler(tool_params)
            
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            })
            
        except Exception as e:
            logger.exception(f"调用工具时出错: {e}")
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"工具执行错误: {str(e)}"
                }
            })
            
    def _handle_get_prompt(self, request_id: Union[str, int, None], params: Dict[str, Any]) -> str:
        """处理获取提示请求
        
        Args:
            request_id: 请求ID
            params: 请求参数
            
        Returns:
            JSON-RPC响应
        """
        prompt_id = params.get('id')
        
        if not prompt_id:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "缺少提示ID"
                }
            })
            
        prompt = self.prompts.get(prompt_id)
        if not prompt:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"提示不存在: {prompt_id}"
                }
            })
            
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": prompt
        })

class MCPServer:
    """MCP服务器类"""
    
    def __init__(self, adapter: Optional[MCPAdapter] = None):
        """初始化MCP服务器
        
        Args:
            adapter: MCP适配器，如果为None则创建新实例
        """
        self.adapter = adapter or MCPAdapter()
        self.running = False
        self.websocket_server = None
        self.clients: Set[WebSocketServerProtocol] = set()
        
        # 设置默认工具和提示
        self._setup_default_tools()
        
    def _setup_default_tools(self) -> None:
        """设置默认工具"""
        # 注册测试工具
        self.adapter.register_tool("test.echo", self._handle_echo)
        
        # 注册默认提示
        self.adapter.register_prompt("default_help", {
            "id": "default_help",
            "title": "MCP服务器帮助",
            "description": "关于MCP服务器的基本信息",
            "content": [
                {
                    "type": "text",
                    "text": "这是一个独立的MCP服务器实现，用于测试目的。"
                },
                {
                    "type": "text",
                    "text": "可用工具:"
                },
                {
                    "type": "list",
                    "items": [
                        "test.echo - 回显输入"
                    ]
                }
            ]
        })
        
    async def _handle_echo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理回显工具
        
        Args:
            params: 工具参数
            
        Returns:
            工具结果
        """
        return {
            "echo": params
        }
        
    async def start(self, host: str = "localhost", port: int = 9876) -> None:
        """启动WebSocket服务器
        
        Args:
            host: 服务器主机名
            port: 服务器端口
        """
        if self.running:
            logger.warning("MCP服务器已经在运行")
            return
            
        try:
            self.running = True
            
            # 启动WebSocket服务器
            self.websocket_server = await websockets.serve(
                self._handle_websocket,
                host,
                port
            )
            
            logger.info(f"MCP WebSocket服务器已启动 ws://{host}:{port}")
            
            # 设置信号处理
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
                except NotImplementedError:
                    # Windows不支持add_signal_handler
                    pass
                    
            # 保持服务器运行
            await self.websocket_server.wait_closed()
            
        except Exception as e:
            self.running = False
            logger.exception(f"启动MCP服务器时出错: {e}")
            raise
            
    async def _handle_websocket(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """处理WebSocket连接
        
        Args:
            websocket: WebSocket连接
            path: 请求路径
        """
        # 添加到客户端列表
        self.clients.add(websocket)
        
        try:
            logger.info(f"新客户端连接: {websocket.remote_address}")
            
            # 处理消息
            async for message in websocket:
                try:
                    logger.debug(f"收到消息: {message[:100]}...")
                    response = await self.adapter.handle_message(message)
                    await websocket.send(response)
                    
                except Exception as e:
                    logger.exception(f"处理WebSocket消息时出错: {e}")
                    error_response = json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": f"内部错误: {str(e)}"
                        }
                    })
                    await websocket.send(error_response)
                    
        except ConnectionClosed:
            logger.info(f"客户端断开连接: {websocket.remote_address}")
            
        except Exception as e:
            logger.exception(f"WebSocket连接处理出错: {e}")
            
        finally:
            # 从客户端列表中移除
            self.clients.remove(websocket)
            
    async def stop(self) -> None:
        """停止服务器"""
        if not self.running:
            return
            
        logger.info("停止MCP服务器...")
        self.running = False
        
        # 关闭所有客户端连接
        if self.clients:
            close_tasks = [client.close() for client in self.clients]
            await asyncio.gather(*close_tasks, return_exceptions=True)
            self.clients.clear()
            
        # 关闭WebSocket服务器
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            self.websocket_server = None
            
        logger.info("MCP服务器已停止")
        
    async def start_stdio(self) -> None:
        """通过标准输入/输出启动MCP服务器"""
        if self.running:
            logger.warning("MCP服务器已经在运行")
            return
            
        self.running = True
        logger.info("通过标准输入/输出启动MCP服务器")
        
        try:
            # 获取标准输入
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            
            loop = asyncio.get_event_loop()
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
            
            # 获取标准输出
            writer_transport, writer_protocol = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin, sys.stdout
            )
            writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, loop)
            
            # 处理标准输入消息
            while self.running:
                # 读取Content-Length行
                header_line = await reader.readline()
                if not header_line:
                    break
                    
                header = header_line.decode('utf-8').strip()
                if not header.startswith("Content-Length:"):
                    continue
                    
                content_length = int(header.replace("Content-Length:", "").strip())
                
                # 读取空行
                await reader.readline()
                
                # 读取内容
                content_bytes = await reader.readexactly(content_length)
                message = content_bytes.decode('utf-8')
                
                # 处理消息
                response = await self.adapter.handle_message(message)
                
                # 发送响应
                response_bytes = response.encode('utf-8')
                header = f"Content-Length: {len(response_bytes)}\r\n\r\n"
                writer.write(header.encode('utf-8'))
                writer.write(response_bytes)
                await writer.drain()
                
        except Exception as e:
            logger.exception(f"标准输入/输出通信出错: {e}")
            
        finally:
            self.running = False
            logger.info("MCP标准输入/输出服务器已停止")

async def test_websocket_server():
    """测试WebSocket服务器"""
    try:
        # 创建服务器实例
        logger.info("创建MCPServer实例")
        server = MCPServer()
        
        # 启动服务器
        host = "localhost"
        port = 9876
        logger.info(f"启动WebSocket服务器: {host}:{port}")
        
        # 创建任务
        server_task = asyncio.create_task(server.start(host, port))
        
        # 等待服务器启动
        logger.info("等待服务器启动...")
        await asyncio.sleep(2)
        
        # 测试连接
        logger.info("测试连接到服务器...")
        import websockets
        
        async with websockets.connect(f"ws://{host}:{port}") as websocket:
            # 发送初始化请求
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }
            
            logger.info(f"发送初始化请求: {json.dumps(init_request)}")
            await websocket.send(json.dumps(init_request))
            
            # 接收响应
            response = await websocket.recv()
            logger.info(f"收到响应: {response}")
            
            # 发送工具列表请求
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "listTools",
                "params": {}
            }
            
            logger.info(f"发送工具列表请求: {json.dumps(tools_request)}")
            await websocket.send(json.dumps(tools_request))
            
            # 接收响应
            response = await websocket.recv()
            logger.info(f"收到响应: {response}")
            
            # 发送工具调用请求
            call_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "callTool",
                "params": {
                    "name": "test.echo",
                    "params": {
                        "message": "Hello, MCP!"
                    }
                }
            }
            
            logger.info(f"发送工具调用请求: {json.dumps(call_request)}")
            await websocket.send(json.dumps(call_request))
            
            # 接收响应
            response = await websocket.recv()
            logger.info(f"收到响应: {response}")
            
            # 发送关闭请求
            shutdown_request = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "shutdown",
                "params": {}
            }
            
            logger.info(f"发送关闭请求: {json.dumps(shutdown_request)}")
            await websocket.send(json.dumps(shutdown_request))
            
            # 接收响应
            response = await websocket.recv()
            logger.info(f"收到响应: {response}")
        
        # 停止服务器
        logger.info("停止服务器...")
        await server.stop()
        
        # 等待服务器任务完成
        try:
            await asyncio.wait_for(server_task, timeout=5)
        except asyncio.TimeoutError:
            logger.warning("服务器任务未在预期时间内完成")
        
        logger.info("测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试WebSocket服务器时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_stdio_server():
    """测试标准输入/输出服务器"""
    try:
        # 创建服务器实例
        logger.info("创建MCPServer实例")
        server = MCPServer()
        
        # 创建管道
        logger.info("创建管道")
        read_pipe, write_pipe = os.pipe()
        
        # 保存原始的标准输入/输出
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        
        try:
            # 重定向标准输入/输出
            sys.stdin = os.fdopen(read_pipe, 'r')
            sys.stdout = os.fdopen(write_pipe, 'w')
            
            # 启动服务器
            logger.info("启动STDIO服务器")
            server_task = asyncio.create_task(server.start_stdio())
            
            # 等待服务器启动
            logger.info("等待服务器启动...")
            await asyncio.sleep(2)
            
            # 发送初始化请求
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }
            
            request_json = json.dumps(init_request)
            request_bytes = request_json.encode('utf-8')
            
            logger.info(f"发送初始化请求: {request_json}")
            header = f"Content-Length: {len(request_bytes)}\r\n\r\n"
            sys.stdout.write(header)
            sys.stdout.write(request_json)
            sys.stdout.flush()
            
            # 等待响应
            logger.info("等待响应...")
            await asyncio.sleep(2)
            
            # 停止服务器
            logger.info("停止服务器...")
            server.running = False
            
            # 等待服务器任务完成
            try:
                await asyncio.wait_for(server_task, timeout=5)
            except asyncio.TimeoutError:
                logger.warning("服务器任务未在预期时间内完成")
            
        finally:
            # 恢复原始的标准输入/输出
            sys.stdin = original_stdin
            sys.stdout = original_stdout
            
            # 关闭管道
            os.close(read_pipe)
            os.close(write_pipe)
        
        logger.info("测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试STDIO服务器时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """主函数"""
    logger.info("开始测试独立MCP服务器")
    
    # 测试WebSocket服务器
    logger.info("测试WebSocket服务器...")
    websocket_success = await test_websocket_server()
    
    # 测试STDIO服务器
    logger.info("测试STDIO服务器...")
    stdio_success = await test_stdio_server()
    
    # 输出结果
    logger.info(f"WebSocket服务器测试结果: {'成功' if websocket_success else '失败'}")
    logger.info(f"STDIO服务器测试结果: {'成功' if stdio_success else '失败'}")
    
    return websocket_success and stdio_success

if __name__ == "__main__":
    try:
        logger.info("启动独立MCP服务器测试脚本")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"测试脚本运行出错: {e}")
        import traceback
        logger.error(traceback.format_exc()) 