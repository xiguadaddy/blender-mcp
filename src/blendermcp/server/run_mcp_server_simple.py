#!/usr/bin/env python3
"""
BlenderMCP服务器 - 简化版

这个脚本提供了BlenderMCP的WebSocket服务器功能，
解决了asyncio导入问题，简化了代码结构。
"""

# 标准库导入（确保asyncio首先导入）
import asyncio
import os
import sys
import json
import time
import logging
import tempfile
import argparse
import signal
import threading
from pathlib import Path

# 第三方库导入
try:
    import websockets
except ImportError:
    print("错误: 未找到websockets模块。请安装: pip install websockets")
    sys.exit(1)

# 设置日志
log_file = os.path.join(tempfile.gettempdir(), "blendermcp_server_simple.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MCPServerSimple")

# 全局变量
active_connections = 0
processed_requests = 0
server_start_time = None
tools_file = os.path.join(tempfile.gettempdir(), "blendermcp_tools.json")
status_file = os.path.join(tempfile.gettempdir(), "blendermcp_status.json")

# 工具定义
TOOLS = [
    {
        "name": "blender.test.echo",
        "description": "回显输入参数",
        "parameters": [
            {"name": "message", "type": "string", "description": "要回显的消息"}
        ]
    }
]

# MCP适配器类
class MCPAdapter:
    """MCP协议适配器"""
    
    def __init__(self):
        self.tools = {}
        self.request_id = 0
        logger.info("初始化MCP适配器")
        
        # 注册默认工具
        self.register_tool(
            "blender.test.echo", 
            self.echo_handler,
            "回显输入参数",
            [{"name": "message", "type": "string", "description": "要回显的消息"}]
        )
    
    async def echo_handler(self, params):
        """回显输入参数"""
        logger.info(f"echo_handler被调用: {params}")
        return {"echo": params}
    
    def register_tool(self, name, handler, description=None, parameters=None):
        """注册工具"""
        logger.info(f"注册工具: {name}")
        self.tools[name] = {
            "handler": handler,
            "description": description or (handler.__doc__ or "").strip(),
            "parameters": parameters or []
        }
        logger.debug(f"工具 {name} 注册成功")
    
    async def handle_message(self, message):
        """处理JSON-RPC消息"""
        try:
            # 解析JSON
            request = json.loads(message)
            
            # 提取请求ID
            request_id = request.get("id", None)
            
            # 处理不同的方法
            method = request.get("method", "")
            params = request.get("params", {})
            
            if method == "mcp.list_tools":
                return await self._handle_list_tools(request_id)
            elif method == "mcp.invoke_tool":
                return await self._handle_tool_invocation(request_id, params)
            else:
                logger.warning(f"未知方法: {method}")
                return self._create_error_response(
                    request_id, -32601, f"未知方法: {method}"
                )
                
        except json.JSONDecodeError:
            logger.error("JSON解析错误")
            return self._create_error_response(None, -32700, "JSON解析错误")
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            logger.exception("消息处理异常")
            return self._create_error_response(
                request_id if 'request_id' in locals() else None, 
                -32603, 
                f"内部错误: {str(e)}"
            )
    
    async def _handle_list_tools(self, request_id):
        """处理工具列表请求"""
        try:
            # 构建工具列表
            tools_list = []
            for name, tool in self.tools.items():
                tool_info = {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
                tools_list.append(tool_info)
            
            # 构建响应
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": tools_list
            }
            
            return json.dumps(response)
        except Exception as e:
            logger.error(f"处理工具列表请求时出错: {str(e)}")
            logger.exception("工具列表异常")
            return self._create_error_response(
                request_id, -32603, f"内部错误: {str(e)}"
            )
    
    async def _handle_tool_invocation(self, request_id, params):
        """处理工具调用请求"""
        try:
            # 获取工具名称
            tool_name = params.get("name", "")
            if not tool_name:
                logger.error("未指定工具名称")
                return self._create_error_response(
                    request_id, -32602, "未指定工具名称"
                )
            
            # 检查工具是否存在
            if tool_name not in self.tools:
                logger.error(f"未找到工具: {tool_name}")
                return self._create_error_response(
                    request_id, -32601, f"未找到工具: {tool_name}"
                )
            
            # 获取工具处理函数
            tool = self.tools[tool_name]
            
            # 可能是直接函数或字典中的handler
            handler = tool if callable(tool) else tool.get("handler")
            
            if not callable(handler):
                logger.error(f"工具处理函数不可调用: {tool_name}")
                return self._create_error_response(
                    request_id, -32603, f"工具处理函数不可调用: {tool_name}"
                )
            
            # 获取参数
            tool_params = params.get("parameters", {})
            
            # 调用工具
            logger.info(f"调用工具 {tool_name}")
            result = await handler(tool_params)
            
            # 构建响应
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
            return json.dumps(response)
        except Exception as e:
            logger.error(f"处理工具调用请求时出错: {str(e)}")
            logger.exception("工具调用异常")
            return self._create_error_response(
                request_id, -32603, f"内部错误: {str(e)}"
            )
    
    def _create_error_response(self, request_id, code, message):
        """创建错误响应"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        return json.dumps(response)

# 保存工具列表到文件
def write_tools_list():
    """将工具列表保存到文件"""
    try:
        with open(tools_file, 'w', encoding='utf-8') as f:
            json.dump(TOOLS, f, indent=2, ensure_ascii=False)
        logger.info(f"工具列表已保存到: {tools_file}")
        return True
    except Exception as e:
        logger.error(f"保存工具列表失败: {e}")
        return False

# 更新状态文件
def update_status_file(host, port, mode):
    """定期更新状态文件"""
    global server_start_time, active_connections, processed_requests
    
    logger.info(f"开始更新状态文件")
    
    while True:
        try:
            # 计算运行时间
            uptime = time.time() - server_start_time
            
            # 创建状态数据
            status_data = {
                "mode": mode,
                "uptime": uptime,
                "connections": active_connections,
                "requests": processed_requests,
                "timestamp": time.time()
            }
            
            # 添加WebSocket特定信息
            if mode == "websocket" and host and port:
                status_data["host"] = host
                status_data["port"] = port
            
            # 写入状态文件
            with open(status_file, 'w') as f:
                json.dump(status_data, f)
            
            # 等待下一次更新
            time.sleep(1)
        
        except Exception as e:
            logger.error(f"更新状态文件时出错: {str(e)}")
            time.sleep(1)

# WebSocket服务器
async def websocket_server(host, port):
    """启动WebSocket服务器"""
    try:
        # 创建MCP适配器
        adapter = MCPAdapter()
        
        # 写入工具列表
        write_tools_list()
        
        # 连接处理函数
        async def handle_connection(websocket):
            global active_connections, processed_requests
            client_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'unknown'
            active_connections += 1
            logger.info(f"新的WebSocket连接: {client_address}")
            
            try:
                async for message in websocket:
                    processed_requests += 1
                    logger.debug(f"收到消息: {message}")
                    try:
                        response = await adapter.handle_message(message)
                        await websocket.send(response)
                        logger.debug(f"发送响应: {response}")
                    except Exception as e:
                        logger.error(f"处理消息时出错: {str(e)}")
                        error_response = json.dumps({
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {
                                "code": -32603,
                                "message": f"内部错误: {str(e)}"
                            }
                        })
                        await websocket.send(error_response)
            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"WebSocket连接关闭: {client_address}, 代码: {e.code}, 原因: {e.reason}")
            except Exception as e:
                logger.error(f"WebSocket连接处理错误: {str(e)}")
                logger.exception("连接处理异常")
            finally:
                active_connections -= 1
                logger.info(f"WebSocket连接结束: {client_address}")
        
        # 启动WebSocket服务器
        logger.info(f"正在启动WebSocket服务器: ws://{host}:{port}")
        server = await websockets.serve(handle_connection, host, port, origins=None)
        logger.info(f"WebSocket服务器已启动: ws://{host}:{port}")
        
        # 根据主机地址输出不同的信息
        if host == "localhost" or host == "127.0.0.1":
            logger.info("注意：服务器绑定在localhost上，仅允许本机连接")
            logger.info("如需允许远程连接，请使用 --host 0.0.0.0")
        elif host == "0.0.0.0":
            logger.info("服务器绑定在所有网络接口上，允许远程连接")
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                logger.info(f"可通过以下WebSocket URL连接: ws://{ip}:{port}")
            except Exception as e:
                logger.error(f"获取本机IP地址失败: {str(e)}")
        
        # 启动状态更新线程
        try:
            status_thread = threading.Thread(target=update_status_file, args=(host, port, "websocket"))
            status_thread.daemon = True
            status_thread.start()
        except Exception as e:
            logger.error(f"启动状态更新线程失败: {str(e)}")
        
        # 等待服务器关闭
        await server.wait_closed()
    
    except Exception as e:
        logger.error(f"WebSocket服务器函数发生严重错误: {str(e)}")
        logger.exception("WebSocket服务器异常")
        raise

# 信号处理函数
def handle_exit_signal(signum, frame):
    """处理退出信号"""
    logger.info(f"收到信号 {signum}，正在关闭服务器")
    
    # 清理操作
    try:
        # 删除状态文件
        if os.path.exists(status_file):
            os.remove(status_file)
            logger.info(f"已删除状态文件: {status_file}")
    except Exception as e:
        logger.warning(f"清理状态文件失败: {str(e)}")
    
    sys.exit(0)

# 主函数
async def main():
    """主函数"""
    global server_start_time
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description="BlenderMCP服务器 - 简化版")
        parser.add_argument("--host", default="localhost", help="WebSocket服务器主机")
        parser.add_argument("--port", type=int, default=9876, help="WebSocket服务器端口")
        parser.add_argument("--debug", action="store_true", help="启用调试模式")
        args = parser.parse_args()
        
        # 设置日志级别
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.info("已启用调试模式")
        
        # 记录启动信息
        logger.info(f"启动BlenderMCP服务器")
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"平台: {sys.platform}")
        logger.info(f"工作目录: {os.getcwd()}")
        
        # 设置服务器启动时间
        server_start_time = time.time()
        
        # 注册信号处理
        try:
            signal.signal(signal.SIGINT, handle_exit_signal)
            signal.signal(signal.SIGTERM, handle_exit_signal)
            logger.info("已注册信号处理器")
        except Exception as e:
            logger.warning(f"注册信号处理器失败: {str(e)}")
        
        # 启动WebSocket服务器
        logger.info(f"启动WebSocket服务器: {args.host}:{args.port}")
        await websocket_server(args.host, args.port)
            
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭服务器")
    except Exception as e:
        logger.error(f"主函数执行失败: {str(e)}")
        logger.exception("主函数异常")
        raise

# 入口点
if __name__ == "__main__":
    try:
        # 确保Windows平台使用正确的事件循环策略
        if sys.platform == 'win32':
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                logger.info("已设置Windows事件循环策略")
            except Exception as e:
                logger.error(f"设置Windows事件循环策略失败: {str(e)}")
        
        # 使用asyncio.run运行主函数
        logger.info("开始运行主函数")
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭服务器")
        
    except Exception as e:
        logger.error(f"启动服务器失败: {str(e)}")
        logger.exception("启动服务器异常")
        print(f"启动服务器失败: {str(e)}")
        sys.exit(1)
        
    finally:
        # 清理工作
        try:
            # 删除状态文件
            if os.path.exists(status_file):
                os.remove(status_file)
                logger.info(f"已删除状态文件: {status_file}")
        except Exception as e:
            logger.warning(f"清理状态文件失败: {str(e)}")
            
        logger.info("服务器已关闭")
        print("服务器已关闭") 