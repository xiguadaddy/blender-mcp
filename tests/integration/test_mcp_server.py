#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BlenderMCP MCP服务器集成测试
"""

import asyncio
import json
import os
import sys
import unittest
import websockets
import tempfile
import time
import subprocess
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_integration_test")

# 测试配置
TEST_HOST = "localhost"
TEST_PORT = 9877  # 使用不同于默认端口的端口，避免冲突
TEST_TIMEOUT = 10  # 超时时间（秒）

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
SERVER_SCRIPT = PROJECT_ROOT / "src" / "blendermcp" / "server" / "run_mcp_server.py"


class MCPServerIntegrationTest(unittest.TestCase):
    """MCP服务器集成测试类"""
    
    @classmethod
    def setUpClass(cls):
        """启动MCP服务器进程"""
        logger.info("启动MCP服务器进程")
        
        # 确保Python路径正确
        python_exe = sys.executable
        
        # 创建临时日志文件
        cls.log_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
        cls.log_file.close()
        
        # 启动服务器进程
        cls.server_process = subprocess.Popen(
            [
                python_exe, 
                str(SERVER_SCRIPT), 
                "--mode", "websocket", 
                "--host", TEST_HOST, 
                "--port", str(TEST_PORT),
                "--log", cls.log_file.name
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        time.sleep(2)
        logger.info(f"MCP服务器进程已启动，PID: {cls.server_process.pid}")
    
    @classmethod
    def tearDownClass(cls):
        """关闭MCP服务器进程"""
        logger.info("关闭MCP服务器进程")
        
        # 终止服务器进程
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.wait(timeout=5)
            logger.info("MCP服务器进程已关闭")
        
        # 输出日志文件内容
        if os.path.exists(cls.log_file.name):
            with open(cls.log_file.name, 'r') as f:
                logger.info(f"服务器日志内容:\n{f.read()}")
            
            # 删除临时日志文件
            os.unlink(cls.log_file.name)
    
    async def connect_to_server(self):
        """连接到MCP服务器"""
        uri = f"ws://{TEST_HOST}:{TEST_PORT}"
        return await websockets.connect(uri)
    
    async def send_request(self, websocket, method, params=None):
        """发送JSON-RPC请求"""
        if params is None:
            params = {}
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        await websocket.send(json.dumps(request))
        response_text = await websocket.recv()
        return json.loads(response_text)
    
    def test_initialize(self):
        """测试初始化请求"""
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                response = await self.send_request(websocket, "initialize")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
                self.assertIn("name", response["result"])
                self.assertIn("version", response["result"])
                self.assertEqual(response["result"]["status"], "ok")
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_list_tools(self):
        """测试列出工具请求"""
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 先初始化
                await self.send_request(websocket, "initialize")
                
                # 列出工具
                response = await self.send_request(websocket, "listTools")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
                self.assertIn("tools", response["result"])
                self.assertIsInstance(response["result"]["tools"], list)
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_call_tool(self):
        """测试调用工具请求"""
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 先初始化
                await self.send_request(websocket, "initialize")
                
                # 列出工具
                tools_response = await self.send_request(websocket, "listTools")
                tools = tools_response["result"]["tools"]
                
                # 如果有工具，测试调用第一个工具
                if tools:
                    first_tool = tools[0]
                    tool_name = first_tool["name"]
                    
                    # 调用工具
                    response = await self.send_request(websocket, "callTool", {
                        "name": tool_name,
                        "params": {}
                    })
                    
                    self.assertEqual(response.get("jsonrpc"), "2.0")
                    self.assertEqual(response.get("id"), 1)
                    self.assertIn("result", response)
                else:
                    logger.warning("没有可用的工具进行测试")
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_shutdown(self):
        """测试关闭请求"""
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 先初始化
                await self.send_request(websocket, "initialize")
                
                # 关闭连接
                response = await self.send_request(websocket, "shutdown")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
                self.assertEqual(response["result"]["status"], "ok")
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_invalid_method(self):
        """测试无效方法请求"""
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 发送无效方法
                response = await self.send_request(websocket, "invalidMethod")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("error", response)
                self.assertEqual(response["error"]["code"], -32601)  # 方法不存在
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_invalid_params(self):
        """测试无效参数请求"""
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 先初始化
                await self.send_request(websocket, "initialize")
                
                # 发送无效参数
                response = await self.send_request(websocket, "callTool", {
                    "invalid_param": "value"
                })
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("error", response)
                self.assertEqual(response["error"]["code"], -32602)  # 无效参数
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_multiple_connections(self):
        """测试多连接并发"""
        async def client_session(client_id):
            websocket = await self.connect_to_server()
            try:
                # 初始化
                response = await self.send_request(websocket, "initialize")
                self.assertEqual(response["result"]["status"], "ok")
                
                # 列出工具
                response = await self.send_request(websocket, "listTools")
                self.assertIn("tools", response["result"])
                
                # 关闭连接
                response = await self.send_request(websocket, "shutdown")
                self.assertEqual(response["result"]["status"], "ok")
                
                return True
            except Exception as e:
                logger.error(f"客户端 {client_id} 出错: {str(e)}")
                return False
            finally:
                await websocket.close()
        
        async def run_test():
            # 创建5个并发客户端
            tasks = [client_session(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            # 验证所有客户端都成功
            self.assertTrue(all(results))
        
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main() 