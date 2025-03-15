#!/usr/bin/env python
"""
MCP服务器启动脚本

此脚本用于启动MCP服务器，支持WebSocket和STDIO模式。
在Blender插件中通过subprocess调用此脚本来启动服务器。
"""

import os
import sys
import json
import logging
import argparse
import asyncio
import signal
import websockets
from pathlib import Path
import tempfile

# 配置日志
log_file = os.path.join(tempfile.gettempdir(), "mcp_server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MCPAdapter:
    """MCP适配器，处理工具和提示"""
    
    def __init__(self):
        """初始化MCP适配器"""
        self.tools = {
            "test.echo": {
                "name": "test.echo",
                "description": "处理回显工具\n        \n        Args:\n            params: 工具参数\n            \n        Returns:\n            工具结果\n        ",
                "inputSchema": {}
            }
        }
    
    def list_tools(self):
        """列出可用工具"""
        return list(self.tools.values())
    
    def call_tool(self, name, params):
        """调用工具"""
        if name == "test.echo":
            return {"echo": params}
        else:
            raise ValueError(f"未知工具: {name}")

class MCPServer:
    """MCP服务器类"""
    
    def __init__(self, host="localhost", port=9876):
        """初始化MCP服务器"""
        self.host = host
        self.port = port
        self.adapter = MCPAdapter()
        self.server = None
        self.running = False
        self.clients = set()
    
    async def handle_message(self, message, send_response):
        """处理JSON-RPC消息"""
        try:
            request = json.loads(message)
            logger.debug(f"收到消息: {message[:50]}...")
            
            if "method" not in request:
                response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "无效请求"},
                    "id": request.get("id", None)
                }
            else:
                method = request["method"]
                params = request.get("params", {})
                
                if method == "initialize":
                    result = {
                        "name": "BlenderMCP",
                        "version": "0.1.0",
                        "status": "ok"
                    }
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": result
                    }
                elif method == "shutdown":
                    result = {"status": "ok"}
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": result
                    }
                    self.running = False
                elif method == "listTools":
                    tools = self.adapter.list_tools()
                    result = {"tools": tools}
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": result
                    }
                elif method == "callTool":
                    tool_name = params["name"]
                    tool_params = params["params"]
                    result = self.adapter.call_tool(tool_name, tool_params)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": result
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32601, "message": f"方法不存在: {method}"},
                        "id": request.get("id", None)
                    }
            
            await send_response(json.dumps(response))
            
            if method == "shutdown":
                return False
            
            return True
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "解析错误"},
                "id": None
            }
            await send_response(json.dumps(response))
            return True
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"内部错误: {str(e)}"},
                "id": request.get("id", None) if "request" in locals() else None
            }
            await send_response(json.dumps(response))
            return True
    
    async def handle_websocket(self, websocket, path):
        """处理WebSocket连接"""
        client_info = websocket.remote_address
        logger.info(f"新客户端连接: {client_info}")
        self.clients.add(websocket)
        
        try:
            async for message in websocket:
                async def send_response(response):
                    await websocket.send(response)
                
                continue_running = await self.handle_message(message, send_response)
                if not continue_running:
                    break
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端断开连接: {client_info}")
        finally:
            self.clients.remove(websocket)
    
    async def start_websocket(self):
        """启动WebSocket服务器"""
        logger.info(f"启动WebSocket服务器: {self.host}:{self.port}")
        self.running = True
        
        self.server = await websockets.serve(
            self.handle_websocket,
            self.host,
            self.port
        )
        
        logger.info(f"MCP WebSocket服务器已启动 ws://{self.host}:{self.port}")
        
        # 保持服务器运行直到关闭
        while self.running:
            await asyncio.sleep(1)
        
        # 关闭服务器
        self.server.close()
        await self.server.wait_closed()
        logger.info("MCP服务器已停止")
    
    async def start_stdio(self):
        """启动标准输入/输出服务器"""
        logger.info("通过标准输入/输出启动MCP服务器")
        self.running = True
        
        # 设置标准输入为二进制模式（仅在Windows上需要）
        if sys.platform == "win32":
            import msvcrt
            import os
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        
        # 创建读取器和写入器
        reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        
        loop = asyncio.get_event_loop()
        
        try:
            await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)
            writer_transport, writer_protocol = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin, sys.stdout
            )
            writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, loop)
            
            # 处理消息
            while self.running:
                # 读取消息长度（4字节整数）
                length_bytes = await reader.readexactly(4)
                length = int.from_bytes(length_bytes, byteorder="big")
                
                # 读取消息内容
                message = await reader.readexactly(length)
                message_str = message.decode("utf-8")
                
                # 处理消息并发送响应
                async def send_response(response):
                    response_bytes = response.encode("utf-8")
                    length_bytes = len(response_bytes).to_bytes(4, byteorder="big")
                    writer.write(length_bytes + response_bytes)
                    await writer.drain()
                
                continue_running = await self.handle_message(message_str, send_response)
                if not continue_running:
                    break
            
        except (asyncio.IncompleteReadError, ConnectionError) as e:
            logger.error(f"标准输入/输出通信出错: {str(e)}", exc_info=True)
        finally:
            logger.info("MCP标准输入/输出服务器已停止")
            if "writer" in locals():
                writer.close()

def handle_signal(sig, frame):
    """处理信号"""
    logger.info(f"收到信号 {sig}，正在关闭服务器...")
    asyncio.get_event_loop().stop()
    sys.exit(0)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动MCP服务器")
    parser.add_argument("--mode", choices=["websocket", "stdio"], default="websocket",
                      help="服务器模式: websocket 或 stdio")
    parser.add_argument("--host", default="localhost", help="WebSocket服务器主机")
    parser.add_argument("--port", type=int, default=9876, help="WebSocket服务器端口")
    args = parser.parse_args()
    
    # 注册信号处理程序
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # 创建服务器
    server = MCPServer(host=args.host, port=args.port)
    
    # 启动服务器
    loop = asyncio.get_event_loop()
    try:
        if args.mode == "websocket":
            logger.info(f"以WebSocket模式启动MCP服务器: {args.host}:{args.port}")
            loop.run_until_complete(server.start_websocket())
        else:
            logger.info("以STDIO模式启动MCP服务器")
            loop.run_until_complete(server.start_stdio())
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭服务器...")
    except Exception as e:
        logger.error(f"启动服务器时出错: {str(e)}", exc_info=True)
    finally:
        loop.close()
        logger.info("MCP服务器已关闭")

if __name__ == "__main__":
    main() 