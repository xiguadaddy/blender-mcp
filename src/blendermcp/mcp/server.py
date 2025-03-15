"""
BlenderMCP MCP服务器

该模块提供了MCP服务器的实现，支持WebSocket和标准输入/输出通信。
"""

import asyncio
import json
import logging
import sys
import signal
import os
from typing import Dict, List, Any, Optional, Union, Set
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from .adapter import MCPAdapter
from .blender_tools import BlenderToolHandler
from ..server.config import ConfigManager

logger = logging.getLogger(__name__)

class MCPServer:
    """MCP服务器类"""
    
    def __init__(self, adapter: Optional[MCPAdapter] = None, config: Optional[ConfigManager] = None):
        """初始化MCP服务器
        
        Args:
            adapter: MCP适配器，如果为None则创建新实例
            config: 配置管理器，如果为None则创建新实例
        """
        self.adapter = adapter or MCPAdapter()
        self.config = config or ConfigManager()
        self.running = False
        self.websocket_server = None
        self.clients: Set[WebSocketServerProtocol] = set()
        
        # 初始化工具处理器
        self.tool_handler = BlenderToolHandler()
        self._setup_default_tools()
        
    def _setup_default_tools(self) -> None:
        """设置默认工具"""
        # 注册Blender工具
        self.adapter.register_tool("blender.get_scene_info", self.tool_handler.handle_get_scene_info)
        self.adapter.register_tool("blender.create_object", self.tool_handler.handle_create_object)
        self.adapter.register_tool("blender.delete_object", self.tool_handler.handle_delete_object)
        self.adapter.register_tool("blender.set_material", self.tool_handler.handle_set_material)
        self.adapter.register_tool("blender.render_image", self.tool_handler.handle_render_image)
        
        # 注册默认提示
        self.adapter.register_prompt("default_help", {
            "id": "default_help",
            "title": "BlenderMCP帮助",
            "description": "关于Blender MCP的基本信息",
            "content": [
                {
                    "type": "text",
                    "text": "BlenderMCP是一个用于Blender的模型上下文协议(MCP)实现，允许AI应用程序与Blender进行通信并控制其功能。"
                },
                {
                    "type": "text",
                    "text": "可用工具:"
                },
                {
                    "type": "list",
                    "items": [
                        "blender.get_scene_info - 获取场景信息",
                        "blender.create_object - 创建新对象",
                        "blender.delete_object - 删除对象",
                        "blender.set_material - 设置材质",
                        "blender.render_image - 渲染图像"
                    ]
                }
            ]
        })
        
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
            
    @staticmethod
    async def main():
        """主入口点，用于命令行运行"""
        import argparse
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 命令行参数
        parser = argparse.ArgumentParser(description="BlenderMCP服务器")
        parser.add_argument(
            "--stdio", 
            action="store_true", 
            help="使用标准输入/输出而不是WebSocket"
        )
        parser.add_argument(
            "--host", 
            default="localhost", 
            help="WebSocket服务器主机名"
        )
        parser.add_argument(
            "--port", 
            type=int, 
            default=9876, 
            help="WebSocket服务器端口"
        )
        parser.add_argument(
            "--config", 
            help="配置文件路径"
        )
        parser.add_argument(
            "--log-level", 
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="日志级别"
        )
        
        args = parser.parse_args()
        
        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, args.log_level))
        
        # 创建配置管理器
        config = ConfigManager()
        if args.config:
            config.load_from_file(args.config)
            
        # 创建服务器
        server = MCPServer(config=config)
        
        try:
            if args.stdio:
                await server.start_stdio()
            else:
                await server.start(args.host, args.port)
                
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
            
        finally:
            await server.stop()
            
if __name__ == "__main__":
    asyncio.run(MCPServer.main()) 