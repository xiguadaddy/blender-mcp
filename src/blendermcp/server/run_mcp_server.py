import asyncio  # 首先导入asyncio，避免其他导入干扰
# MCP服务器实现方案：
# 1. 服务器核心采用 asyncio 与 websockets 处理异步消息，支持远程工具调用；
# 2. 与Blender通信采用 multiprocessing 队列进行进程间通信。

# 先导入所有标准库模块
import os
import sys
import json
import time
import argparse
import tempfile
import logging
import signal
import threading
from pathlib import Path
import http.server
import importlib.util
import traceback  # 添加traceback模块用于详细错误信息

# 设置日志
log_file = os.path.join(tempfile.gettempdir(), "blendermcp_server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MCPServer")

# 确保Windows平台使用正确的事件循环策略
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("已设置Windows事件循环策略")
    except Exception as e:
        logger.error(f"设置Windows事件循环策略失败: {str(e)}")

# 尝试导入websockets
try:
    import websockets
    logger.info("成功导入websockets模块")
except ImportError:
    logger.error("无法导入websockets模块，请安装: pip install websockets")
    raise

# 添加包路径
package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)
    logger.info(f"已添加包路径: {package_dir}")

# 尝试导入IPC模块
try:
    from blendermcp.common.ipc import init_queues, cleanup_queues, handle_blender_response, send_request_to_blender, start_response_listener
    logger.info("成功导入IPC模块")
except ImportError:
    logger.error("无法导入IPC模块")
    raise

# 保存原始模块状态，避免修改现有模块
original_modules = set(sys.modules.keys())

# 定义简单的工具注册函数，避免导入循环依赖
def register_default_tools(adapter):
    """注册默认工具，不依赖外部模块"""
    logger.info("注册默认工具")
    
    def echo_handler(params):
        """回显输入参数"""
        logger.info(f"echo_handler被调用: {params}")
        return {"echo": params}
    
    adapter.register_tool(
        "server.test.echo", 
        echo_handler,
        "回显输入参数",
        [{"name": "message", "type": "string", "description": "要回显的消息"}]
    )
    
    logger.info("默认工具注册完成")

# 初始化IPC队列
init_queues()

# 启动响应监听器线程
response_listener_thread = start_response_listener(handle_blender_response)

# 安全导入工具模块，避免循环依赖
try:
    # 尝试导入tools包和模块
    logger.info("尝试导入工具模块")
    import importlib
    
    # 首先尝试直接导入
    try:
        tools_module = importlib.import_module("blendermcp.tools")
        logger.info("成功导入tools模块")
        
        # 从模块获取注册函数
        register_all_tools = getattr(tools_module, "register_all_tools", None)
        get_tools_info = getattr(tools_module, "get_tools_info", None)
        
        if register_all_tools is None:
            logger.warning("tools模块中没有register_all_tools函数，将使用默认实现")
            register_all_tools = register_default_tools
        
        if get_tools_info is None:
            logger.warning("tools模块中没有get_tools_info函数，将使用默认实现")
            get_tools_info = lambda: []
            
    except ImportError as e:
        logger.warning(f"导入tools模块失败: {str(e)}")
        register_all_tools = register_default_tools
        get_tools_info = lambda: []
except Exception as e:
    logger.error(f"导入工具模块时出错: {str(e)}")
    # 定义默认工具注册函数，确保服务器可以启动
    register_all_tools = register_default_tools
    get_tools_info = lambda: []

# 全局变量
active_connections = 0
processed_requests = 0
server_start_time = None
status_update_interval = 1  # 状态更新间隔（秒）

# MCP适配器类
class MCPAdapter:
    """MCP工具适配器"""
    
    def __init__(self):
        self.tools = {}  # 工具名称 -> 处理函数
        self.tools_info = {}  # 工具名称 -> 工具信息
    
    def register_tool(self, name, handler, description=None, parameters=None):
        """注册工具"""
        self.tools[name] = handler
        self.tools_info[name] = {
            "name": name,
            "description": description or "",
            "parameters": parameters or []
        }
        logger.info(f"已注册工具: {name}")
        
    def get_tools_info(self):
        """获取所有工具信息"""
        return self.tools_info
        
    async def handle_message(self, message):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            logger.debug(f"收到消息: {data}")
            
            request_id = data.get("id", "unknown")
            
            if "method" not in data:
                return self._create_error_response(request_id, -32600, "Invalid Request: missing method")
            
            method = data["method"]
            
            if method == "mcp/list_tools":
                return await self._handle_list_tools(request_id)
            elif method == "mcp/invoke":
                params = data.get("params", {})
                return await self._handle_tool_invocation(request_id, params)
            else:
                return self._create_error_response(request_id, -32601, f"Method not found: {method}")
                
        except json.JSONDecodeError:
            return self._create_error_response("unknown", -32700, "Parse error: invalid JSON")
        except Exception as e:
            logger.error(f"处理消息错误: {str(e)}")
            return self._create_error_response("unknown", -32603, f"Internal error: {str(e)}")
    
    async def _handle_list_tools(self, request_id):
        """处理列出工具请求"""
        tools_list = []
        for name, info in self.tools_info.items():
            tools_list.append({
                "name": name,
                "description": info["description"],
                "parameters": info["parameters"]
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools_list
            }
        }
        
    async def _handle_tool_invocation(self, request_id, params):
        """处理工具调用请求"""
        if "tool" not in params:
            return self._create_error_response(request_id, -32602, "Invalid params: missing tool name")
        
        tool_name = params["tool"]
        tool_params = params.get("params", {})
        
        logger.info(f"工具调用: {tool_name}, 参数: {tool_params}")
        
        if tool_name in self.tools:
            try:
                # 直接处理的工具
                handler = self.tools[tool_name]
                
                # 检查是否为需要转发到Blender的工具
                if tool_name.startswith("blender."):
                    # 使用IPC机制发送请求到Blender
                    request = {
                        "tool": tool_name.replace("blender.", ""),  # 移除前缀
                        "params": tool_params
                    }
                    
                    # 等待Blender响应
                    response = send_request_to_blender(request)
                    
                    # 包装结果
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": response
                    }
                else:
                    # 在服务器进程中处理的工具
                    result = handler(tool_params)
                    
                    # 包装结果
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
            except Exception as e:
                logger.error(f"工具执行错误: {str(e)}\n{traceback.format_exc()}")
                return self._create_error_response(request_id, -32603, f"Tool execution error: {str(e)}")
        else:
            return self._create_error_response(request_id, -32601, f"Tool not found: {tool_name}")
    
    def _create_error_response(self, request_id, code, message):
        """创建错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

# 保存工具列表到文件
def write_tools_list(adapter):
    """将工具列表保存到文件
    
    Args:
        adapter: MCP适配器实例
        
    Returns:
        bool: 是否成功写入文件
    """
    tools_file = os.path.join(tempfile.gettempdir(), "blendermcp_tools.json")
    logger.info(f"准备写入工具列表到文件: {tools_file}")
    
    try:
        # 获取工具列表
        tools_list = adapter.get_tools_info()
        
        # 确保至少有一个工具
        if not tools_list:
            tools_list = [
                {
                    "name": "blender.test.echo",
                    "description": "回显输入参数",
                    "parameters": [
                        {"name": "message", "type": "string", "description": "要回显的消息"}
                    ]
                }
            ]
        
        # 按名称排序工具列表
        try:
            tools_list.sort(key=lambda x: x["name"])
        except Exception as e:
            logger.error(f"排序工具列表时出错: {str(e)}")
        
        # 写入文件
        with open(tools_file, 'w', encoding='utf-8') as f:
            json.dump(tools_list, f, indent=2, ensure_ascii=False)
        logger.info(f"工具列表已写入文件: {tools_file}, 共{len(tools_list)}个工具")
        return True
    
    except Exception as e:
        logger.error(f"写入工具列表过程中发生严重错误: {str(e)}")
        logger.exception("写入工具列表异常")
        
        # 紧急情况下，写入基本工具列表
        try:
            fallback_tools = [
                {
                    "name": "blender.test.echo",
                    "description": "回显输入参数",
                    "parameters": [
                        {"name": "message", "type": "string", "description": "要回显的消息"}
                    ]
                }
            ]
            with open(tools_file, 'w', encoding='utf-8') as f:
                json.dump(fallback_tools, f, indent=2, ensure_ascii=False)
            logger.info(f"已写入基本工具列表作为后备: {tools_file}")
            return True
        except:
            logger.critical("无法写入任何工具列表")
            return False

# 更新状态文件
def update_status_file(host, port, mode):
    """定期更新状态文件"""
    global server_start_time, active_connections, processed_requests
    
    logger.info(f"开始更新状态文件")
    status_file = os.path.join(tempfile.gettempdir(), "blendermcp_status.json")
    
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
            time.sleep(status_update_interval)
        
        except Exception as e:
            logger.error(f"更新状态文件时出错: {str(e)}")
            logger.exception("状态更新异常")
            time.sleep(status_update_interval)

# WebSocket服务器
async def websocket_server(host, port):
    """启动WebSocket服务器"""
    try:
        # 创建MCP适配器
        adapter = MCPAdapter()
        
        # 注册所有工具
        logger.info("注册所有工具")
        try:
            register_all_tools(adapter)
        except Exception as e:
            logger.error(f"注册工具时出错: {str(e)}")
            logger.error(f"工具注册错误堆栈: {traceback.format_exc()}")
            # 继续执行，即使没有工具也可以启动服务器
            # 注册一个基本的echo工具作为后备
            register_default_tools(adapter)
        
        # 写入工具列表
        logger.info("写入工具列表")
        try:
            write_tools_list(adapter)
        except Exception as e:
            logger.error(f"写入工具列表时出错: {str(e)}")
            # 继续执行，工具列表不是关键功能
        
        # HTTP处理器类
        class MCPHTTPHandler(http.server.BaseHTTPRequestHandler):
            def __init__(self, *args, adapter=None, **kwargs):
                self.adapter = adapter
                super().__init__(*args, **kwargs)
                
            def log_message(self, format, *args):
                logger.info(format % args)
                
            def do_GET(self):
                if self.path == "/tools":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    tools = self.adapter.get_tools_info() if self.adapter else []
                    self.wfile.write(json.dumps(tools).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Not Found")
                    
            def do_POST(self):
                if self.path == "/rpc":
                    content_length = int(self.headers["Content-Length"])
                    post_data = self.rfile.read(content_length).decode()
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    response = loop.run_until_complete(
                        self.adapter.handle_message(post_data)
                    )
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(response.encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Not Found")
        
        # 启动HTTP服务器（使用异步安全的方式）
        logger.info("启动HTTP服务器")
        try:
            def run_http_server(host, port, adapter):
                """运行HTTP服务器"""
                # 创建处理器类
                handler_class = lambda *args, **kwargs: MCPHTTPHandler(*args, adapter=adapter, **kwargs)
                
                # 创建服务器
                server = http.server.HTTPServer((host, port), handler_class)
                logger.info(f"HTTP服务器已启动: http://{host}:{port}")
                
                # 运行服务器
                server.serve_forever()
                
            http_thread = threading.Thread(target=run_http_server, args=(host, port+1, adapter))
            http_thread.daemon = True
            http_thread.start()
        except Exception as e:
            logger.error(f"启动HTTP服务器线程失败: {str(e)}")
            logger.exception("HTTP服务器启动异常")
            # HTTP服务器不是关键功能，可以继续
        
        # 连接处理函数
        logger.info("定义连接处理函数")
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
                        logger.exception("消息处理异常")
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
        
        # 使用直接的操作方式来创建WebSocket服务器，避免使用websockets.serve
        logger.info(f"正在启动WebSocket服务器: ws://{host}:{port}")
        
        try:
            # 直接使用更底层的方法创建WebSocket服务器，避免可能导致asyncio导入中断的问题
            import socket
            
            # 创建套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen(128)
            sock.setblocking(False)
            
            logger.info(f"已创建WebSocket监听套接字: {host}:{port}")
            
            # 创建服务器对象
            from websockets.legacy.server import WebSocketServerProtocol, serve
            
            server = await serve(
                handle_connection, 
                None, 
                None,
                sock=sock,
                origins=None
            )
            
            logger.info(f"WebSocket服务器已启动: ws://{host}:{port}")
            
            # 如果主机是localhost，添加额外的提示
            if host == "localhost" or host == "127.0.0.1":
                logger.info("注意：服务器绑定在localhost上，仅允许本机连接")
                logger.info("如需允许远程连接，请使用 --host 0.0.0.0")
            elif host == "0.0.0.0":
                logger.info("服务器绑定在所有网络接口上，允许远程连接")
                # 获取本机IP地址
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
                # 状态更新不是关键功能，可以继续
            
            # 等待服务器关闭
            await server.wait_closed()
            
        except Exception as e:
            logger.error(f"启动WebSocket服务器失败: {str(e)}")
            logger.error(f"WebSocket服务器错误堆栈: {traceback.format_exc()}")
            
            # 如果启动失败，尝试使用更简单的方法（类似于简化版服务器的方法）
            logger.info("尝试使用备用方法启动WebSocket服务器")
            try:
                # 导入必要的库并使用更简单的方式创建服务器
                import asyncio
                import websockets
                
                # 确保WebSocket处理函数正确
                server = await websockets.serve(
                    handle_connection, 
                    host, 
                    port,
                    origins=None
                )
                
                logger.info(f"使用备用方法成功启动WebSocket服务器: ws://{host}:{port}")
                await server.wait_closed()
                
            except Exception as e2:
                logger.error(f"备用方法启动WebSocket服务器也失败: {str(e2)}")
                logger.error(f"备用方法错误堆栈: {traceback.format_exc()}")
                logger.critical("由于无法启动WebSocket服务器，建议使用简化版服务器 run_mcp_server_simple.py")
                raise
            
    except Exception as e:
        logger.error(f"WebSocket服务器函数发生严重错误: {str(e)}")
        logger.error(f"严重错误堆栈: {traceback.format_exc()}")
        raise

# 标准输入输出服务器
async def stdio_server():
    """启动STDIO服务器"""
    try:
        # 创建MCP适配器
        adapter = MCPAdapter()
        
        # 注册所有工具
        logger.info("注册所有工具")
        try:
            register_all_tools(adapter)
        except Exception as e:
            logger.error(f"注册工具时出错: {str(e)}")
            logger.error(f"工具注册错误堆栈: {traceback.format_exc()}")
            # 继续执行，即使没有工具也可以启动服务器
            # 注册一个基本的echo工具作为后备
            register_default_tools(adapter)
        
        # 写入工具列表
        logger.info("写入工具列表")
        try:
            write_tools_list(adapter)
        except Exception as e:
            logger.error(f"写入工具列表时出错: {str(e)}")
            # 继续执行，工具列表不是关键功能
        
        # 启动状态更新线程
        try:
            status_thread = threading.Thread(target=update_status_file, args=(None, None, "stdio"))
            status_thread.daemon = True
            status_thread.start()
        except Exception as e:
            logger.error(f"启动状态更新线程失败: {str(e)}")
            # 状态更新不是关键功能，可以继续
        
        # 读取标准输入的协程
        async def read_stdin():
            logger.info("开始读取标准输入")
            while True:
                try:
                    # 从标准输入读取一行
                    line = await asyncio.to_thread(sys.stdin.readline)
                    
                    # 如果达到文件结尾，退出循环
                    if not line:
                        logger.info("到达标准输入的文件结尾，关闭服务器")
                        break
                    
                    # 处理消息
                    logger.debug(f"收到消息: {line.strip()}")
                    response = await adapter.handle_message(line)
                    
                    # 发送响应
                    print(response, flush=True)
                    logger.debug(f"发送响应: {response}")
                    
                except Exception as e:
                    logger.error(f"处理标准输入时出错: {str(e)}")
                    logger.exception("标准输入处理异常")
                    error_response = json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": f"内部错误: {str(e)}"
                        }
                    })
                    print(error_response, flush=True)
        
        # 运行读取标准输入的协程
        logger.info("启动STDIO服务器")
        await read_stdin()
        
    except Exception as e:
        logger.error(f"STDIO服务器函数出错: {str(e)}")
        logger.error(f"STDIO服务器错误堆栈: {traceback.format_exc()}")
        raise

# 信号处理
def handle_exit_signal(signum, frame):
    """处理退出信号"""
    logger.info(f"接收到信号 {signum}，正在退出...")
    
    # 清理IPC队列
    cleanup_queues()
    
    # 删除状态文件
    status_file = Path(tempfile.gettempdir()) / "blendermcp_server_status.json"
    if status_file.exists():
        status_file.unlink()
    
    # 强制退出程序
    os._exit(0)

# 主函数
async def main():
    """主函数"""
    global server_start_time
    
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description="MCP服务器")
        parser.add_argument("--mode", choices=["websocket", "stdio"], default="websocket", help="服务器模式")
        parser.add_argument("--host", default="localhost", help="WebSocket服务器主机")
        parser.add_argument("--port", type=int, default=9876, help="WebSocket服务器端口")
        parser.add_argument("--debug", action="store_true", help="启用调试模式")
        args = parser.parse_args()
        
        # 设置日志级别
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.info("已启用调试模式")
        
        # 记录启动信息
        logger.info(f"启动MCP服务器，模式: {args.mode}")
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
        
        # 启动服务器
        if args.mode == "websocket":
            logger.info(f"启动WebSocket服务器: {args.host}:{args.port}")
            await websocket_server(args.host, args.port)
        else:
            logger.info("启动STDIO服务器")
            await stdio_server()
            
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭服务器")
    except Exception as e:
        logger.error(f"主函数执行失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise

# 入口点
if __name__ == "__main__":
    try:
        # 检查是否已有事件循环运行
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.warning("检测到事件循环已在运行，创建新的事件循环")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except Exception as e:
            logger.warning(f"获取事件循环时出错: {str(e)}，创建新的事件循环")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 使用asyncio.run运行主函数
        logger.info("开始运行主函数")
        
        # 尝试使用不同的方法运行主函数，以避免asyncio导入问题
        try:
            # 方法1: 使用asyncio.run (推荐的方法，但可能会出现导入问题)
            asyncio.run(main())
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.error(f"使用asyncio.run时出错: {str(e)}")
            logger.warning("尝试使用备用方法运行主函数")
            
            try:
                # 方法2: 使用事件循环的run_until_complete
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(main())
                loop.close()
            except Exception as e2:
                logger.error(f"使用备用方法1运行主函数时出错: {str(e2)}")
                logger.warning("尝试使用最后的备用方法运行主函数")
                
                # 方法3: 创建一个简单的服务器实现，不依赖复杂的asyncio功能
                try:
                    # 解析命令行参数
                    parser = argparse.ArgumentParser(description="MCP服务器")
                    parser.add_argument("--mode", choices=["websocket", "stdio"], default="websocket", help="服务器模式")
                    parser.add_argument("--host", default="localhost", help="WebSocket服务器主机")
                    parser.add_argument("--port", type=int, default=9876, help="WebSocket服务器端口")
                    parser.add_argument("--debug", action="store_true", help="启用调试模式")
                    args = parser.parse_args()
                    
                    # 设置日志级别
                    if args.debug:
                        logger.setLevel(logging.DEBUG)
                        logger.info("已启用调试模式")
                    
                    # 记录启动信息
                    logger.info(f"使用备用方法3启动服务器，模式: {args.mode}")
                    
                    if args.mode == "websocket":
                        logger.info(f"尝试使用备用WebSocket服务器实现: {args.host}:{args.port}")
                        
                        # 导入必要的库
                        import asyncio
                        import websockets
                        
                        # 创建MCP适配器
                        adapter = MCPAdapter()
                        
                        # 注册工具
                        try:
                            register_all_tools(adapter)
                        except Exception as e:
                            logger.error(f"注册工具时出错: {str(e)}")
                            register_default_tools(adapter)
                        
                        # 写入工具列表
                        try:
                            write_tools_list(adapter)
                        except Exception as e:
                            logger.error(f"写入工具列表时出错: {str(e)}")
                        
                        # 连接处理函数
                        async def handle_connection(websocket, path):
                            global active_connections, processed_requests
                            active_connections += 1
                            logger.info(f"新的WebSocket连接: {websocket.remote_address}")
                            
                            try:
                                async for message in websocket:
                                    processed_requests += 1
                                    response = await adapter.handle_message(message)
                                    await websocket.send(response)
                            except Exception as e:
                                logger.error(f"处理WebSocket连接时出错: {str(e)}")
                            finally:
                                active_connections -= 1
                                logger.info(f"WebSocket连接结束: {websocket.remote_address}")
                        
                        # 启动WebSocket服务器
                        try:
                            # 设置服务器启动时间
                            server_start_time = time.time()
                            
                            # 启动状态更新线程
                            status_thread = threading.Thread(
                                target=update_status_file, 
                                args=(args.host, args.port, "websocket")
                            )
                            status_thread.daemon = True
                            status_thread.start()
                            
                            # 创建和启动服务器
                            start_server = websockets.serve(
                                handle_connection, 
                                args.host, 
                                args.port,
                                origins=None
                            )
                            
                            loop = asyncio.get_event_loop()
                            server = loop.run_until_complete(start_server)
                            logger.info(f"WebSocket服务器已启动: ws://{args.host}:{args.port}")
                            
                            # 运行事件循环
                            loop.run_forever()
                        except Exception as e:
                            logger.error(f"启动WebSocket服务器时出错: {str(e)}")
                            logger.critical("所有方法都失败，请使用简化版服务器 run_mcp_server_simple.py")
                            raise
                    else:
                        logger.info("尝试使用备用STDIO服务器实现")
                        
                        # 创建MCP适配器
                        adapter = MCPAdapter()
                        
                        # 注册工具
                        try:
                            register_all_tools(adapter)
                        except Exception as e:
                            logger.error(f"注册工具时出错: {str(e)}")
                            register_default_tools(adapter)
                        
                        # 写入工具列表
                        try:
                            write_tools_list(adapter)
                        except Exception as e:
                            logger.error(f"写入工具列表时出错: {str(e)}")
                        
                        # 设置服务器启动时间
                        server_start_time = time.time()
                        
                        # 启动状态更新线程
                        status_thread = threading.Thread(
                            target=update_status_file, 
                            args=(None, None, "stdio")
                        )
                        status_thread.daemon = True
                        status_thread.start()
                        
                        # 处理标准输入
                        while True:
                            try:
                                line = sys.stdin.readline()
                                if not line:
                                    break
                                
                                # 创建事件循环处理消息
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                response = loop.run_until_complete(adapter.handle_message(line))
                                print(response, flush=True)
                            except Exception as e:
                                logger.error(f"处理标准输入时出错: {str(e)}")
                                error_response = json.dumps({
                                    "jsonrpc": "2.0",
                                    "id": None,
                                    "error": {
                                        "code": -32603,
                                        "message": f"内部错误: {str(e)}"
                                    }
                                })
                                print(error_response, flush=True)
                
                except Exception as e:
                    logger.error(f"使用最后的备用方法时出错: {str(e)}")
                    logger.critical("所有启动方法都失败，请使用简化版服务器或检查环境配置")
                    print(f"启动服务器失败: {str(e)}")
                    print("所有方法都失败，请使用简化版服务器 run_mcp_server_simple.py")
                    sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭服务器")
        
    except Exception as e:
        logger.error(f"启动服务器失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        print(f"启动服务器失败: {str(e)}")
        print("建议使用简化版服务器 run_mcp_server_simple.py")
        sys.exit(1)
        
    finally:
        # 清理工作
        try:
            # 删除状态文件
            status_file = os.path.join(tempfile.gettempdir(), "blendermcp_status.json")
            if os.path.exists(status_file):
                os.remove(status_file)
                logger.info(f"已删除状态文件: {status_file}")
        except Exception as e:
            logger.warning(f"清理状态文件失败: {str(e)}")
            
        logger.info("服务器已关闭")
        print("服务器已关闭")
