#!/usr/bin/env python
"""
直接测试MCP服务器脚本

该脚本直接导入MCP服务器模块，避免通过blendermcp包导入。
"""

import os
import sys
import logging
import tempfile
import asyncio
import json
import time
import traceback
from pathlib import Path

# 配置日志
log_file = os.path.join(tempfile.gettempdir(), 'direct_mcp_server_test.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_file,
    filemode='a'
)

logger = logging.getLogger(__name__)

def get_project_root():
    """获取项目根目录"""
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取项目根目录（假设脚本在src/blendermcp/scripts目录下）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    logger.info(f"项目根目录: {project_root}")
    return project_root

async def test_websocket_server():
    """测试WebSocket服务器"""
    try:
        # 添加项目根目录到Python路径
        project_root = get_project_root()
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # 直接导入MCP服务器模块
        logger.info("直接导入MCP服务器模块")
        sys.path.insert(0, os.path.join(project_root, 'src'))
        
        # 导入必要的模块
        from blendermcp.mcp.server import MCPServer
        from blendermcp.mcp.adapter import MCPAdapter
        
        # 创建服务器实例
        logger.info("创建MCPServer实例")
        adapter = MCPAdapter()
        server = MCPServer(adapter=adapter)
        
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
            
            # 发送关闭请求
            shutdown_request = {
                "jsonrpc": "2.0",
                "id": 3,
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
        logger.error(traceback.format_exc())
        return False

async def main():
    """主函数"""
    logger.info("开始直接测试MCP服务器")
    
    # 测试WebSocket服务器
    logger.info("测试WebSocket服务器...")
    websocket_success = await test_websocket_server()
    
    # 输出结果
    logger.info(f"WebSocket服务器测试结果: {'成功' if websocket_success else '失败'}")
    
    return websocket_success

if __name__ == "__main__":
    try:
        logger.info("启动直接测试脚本")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"测试脚本运行出错: {e}")
        logger.error(traceback.format_exc()) 