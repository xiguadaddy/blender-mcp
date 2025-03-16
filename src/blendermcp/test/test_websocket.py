#!/usr/bin/env python3
"""
BlenderMCP WebSocket测试客户端

这个脚本用于测试与BlenderMCP服务器的WebSocket连接和工具调用。
"""

import asyncio
import json
import websockets
import os
import tempfile

# 配置参数
HOST = "localhost"
PORT = 9876
WEBSOCKET_URL = f"ws://{HOST}:{PORT}"

# 创建请求
def create_request(method, params, request_id=1):
    """创建一个JSON-RPC请求"""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params
    })

# 测试连接和工具列表
async def test_connection():
    """测试与服务器的连接并获取工具列表"""
    print(f"测试连接到: {WEBSOCKET_URL}")
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            print(f"已连接到: {WEBSOCKET_URL}")
            
            # 发送工具列表请求
            req = create_request("mcp.list_tools", {})
            print(f">>> 发送: {req}")
            await websocket.send(req)
            
            # 接收响应
            response = await websocket.recv()
            print(f"<<< 接收: {response}")
            
            # 解析响应
            resp_data = json.loads(response)
            tools = resp_data.get("result", [])
            print(f"可用工具数量: {len(tools)}")
            
            # 打印工具列表
            for i, tool in enumerate(tools):
                print(f"{i+1}. {tool['name']} - {tool['description']}")
            
            return True
    except Exception as e:
        print(f"连接失败: {str(e)}")
        return False

# 测试测试工具
async def test_echo_tool():
    """测试echo工具"""
    print(f"测试echo工具")
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            # 发送echo工具请求
            params = {
                "name": "blender.test.echo",
                "parameters": {
                    "message": "Hello, BlenderMCP!"
                }
            }
            req = create_request("mcp.invoke_tool", params)
            print(f">>> 发送: {req}")
            await websocket.send(req)
            
            # 接收响应
            response = await websocket.recv()
            print(f"<<< 接收: {response}")
            
            # 解析响应
            resp_data = json.loads(response)
            result = resp_data.get("result", {})
            print(f"响应结果: {result}")
            
            # 检查结果
            echo_message = result.get("echo", {}).get("message")
            if echo_message == "Hello, BlenderMCP!":
                print("测试成功: 收到了正确的回显消息")
                return True
            else:
                print(f"测试失败: 收到了错误的回显消息: {echo_message}")
                return False
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return False

# 检查工具列表文件
def check_tools_list_file():
    """检查工具列表文件是否存在并包含工具"""
    tools_file = os.path.join(tempfile.gettempdir(), "blendermcp_tools.json")
    if os.path.exists(tools_file):
        try:
            with open(tools_file, 'r') as f:
                tools = json.load(f)
            print(f"工具列表文件存在，包含 {len(tools)} 个工具")
            return True
        except Exception as e:
            print(f"读取工具列表文件失败: {str(e)}")
            return False
    else:
        print(f"工具列表文件不存在: {tools_file}")
        return False

# 主函数
async def main():
    """主函数"""
    print("BlenderMCP WebSocket测试客户端")
    print("==============================")
    
    # 检查工具列表文件
    check_tools_list_file()
    
    # 测试连接
    connection_ok = await test_connection()
    if not connection_ok:
        print("连接测试失败，退出")
        return
    
    # 测试echo工具
    await test_echo_tool()

# 入口点
if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main()) 