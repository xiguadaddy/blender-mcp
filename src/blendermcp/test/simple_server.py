#!/usr/bin/env python3
"""
简单的WebSocket服务器

这个脚本提供了一个基本的WebSocket服务器，用于测试与BlenderMCP的连接。
该服务器能够响应基本的JSON-RPC请求并提供测试工具。
"""

import asyncio
import websockets
import json
import logging
import sys
import os
import tempfile

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(tempfile.gettempdir(), "simple_server.log"))
    ]
)
logger = logging.getLogger("SimpleServer")

# 定义测试工具
TOOLS = [
    {
        "name": "blender.test.echo",
        "description": "回显输入参数",
        "parameters": [
            {"name": "message", "type": "string", "description": "要回显的消息"}
        ]
    }
]

# 保存工具列表到文件
def save_tools_list():
    """将工具列表保存到临时文件"""
    try:
        tools_file = os.path.join(tempfile.gettempdir(), "blendermcp_tools.json")
        with open(tools_file, 'w', encoding='utf-8') as f:
            json.dump(TOOLS, f, indent=2, ensure_ascii=False)
        logger.info(f"工具列表已保存到: {tools_file}")
        return True
    except Exception as e:
        logger.error(f"保存工具列表失败: {e}")
        return False

# 处理WebSocket连接
async def handle_connection(websocket, path):
    """处理WebSocket连接"""
    client_address = websocket.remote_address
    logger.info(f"新连接: {client_address}")
    
    try:
        async for message in websocket:
            try:
                # 解析JSON-RPC请求
                request = json.loads(message)
                logger.info(f"收到请求: {request}")
                
                # 构造响应
                response = {"jsonrpc": "2.0", "id": request.get("id")}
                
                # 处理方法调用
                if "method" in request:
                    method = request["method"]
                    params = request.get("params", {})
                    
                    # 工具列表请求
                    if method == "mcp.list_tools":
                        response["result"] = TOOLS
                    
                    # 工具调用请求
                    elif method == "mcp.invoke_tool":
                        tool_name = params.get("name")
                        tool_params = params.get("parameters", {})
                        
                        if tool_name == "blender.test.echo":
                            response["result"] = {"echo": tool_params}
                        else:
                            response["error"] = {
                                "code": -32601,
                                "message": f"未知工具: {tool_name}"
                            }
                    
                    # 未知方法
                    else:
                        response["error"] = {
                            "code": -32601,
                            "message": f"未知方法: {method}"
                        }
                
                # 无效请求
                else:
                    response["error"] = {
                        "code": -32600,
                        "message": "无效请求"
                    }
                
                # 发送响应
                await websocket.send(json.dumps(response))
                logger.info(f"发送响应: {response}")
                
            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "解析错误"
                    }
                }
                await websocket.send(json.dumps(error_response))
            
            except Exception as e:
                logger.error(f"处理请求出错: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if "request" in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"内部错误: {str(e)}"
                    }
                }
                await websocket.send(json.dumps(error_response))
    
    except Exception as e:
        logger.error(f"连接处理错误: {e}")
    
    finally:
        logger.info(f"连接关闭: {client_address}")

# 主函数
async def main():
    """启动WebSocket服务器"""
    host = "0.0.0.0"
    port = 9876
    
    # 保存工具列表
    save_tools_list()
    
    # 启动服务器
    logger.info(f"启动WebSocket服务器: ws://{host}:{port}")
    server = await websockets.serve(handle_connection, host, port)
    logger.info(f"服务器已启动，监听: {host}:{port}")
    
    # 输出本地IP地址，方便连接
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        logger.info(f"本地IP地址: {local_ip}")
        logger.info(f"可通过以下地址访问: ws://{local_ip}:{port}")
    except:
        pass
    
    # 等待服务器关闭
    await server.wait_closed()

# 入口点
if __name__ == "__main__":
    try:
        # 设置正确的事件循环策略（Windows平台）
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # 运行主函数
        asyncio.run(main())
    
    except KeyboardInterrupt:
        logger.info("接收到中断信号，关闭服务器")
    
    except Exception as e:
        logger.error(f"服务器错误: {e}")
        logger.exception("服务器异常堆栈:")
    
    finally:
        logger.info("服务器已关闭")
        print("服务器已关闭") 