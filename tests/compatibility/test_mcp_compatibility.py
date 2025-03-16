#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BlenderMCP MCP服务器兼容性测试
"""

import asyncio
import json
import os
import sys
import platform
import unittest
import websockets
import tempfile
import subprocess
import logging
import argparse
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_compatibility_test")

# 测试配置
TEST_HOST = "localhost"
TEST_PORT = 9880  # 使用不同于默认端口的端口，避免冲突
TEST_TIMEOUT = 10  # 超时时间（秒）

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
SERVER_SCRIPT = PROJECT_ROOT / "src" / "blendermcp" / "server" / "run_mcp_server.py"


class MCPCompatibilityTest(unittest.TestCase):
    """MCP服务器兼容性测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        logger.info("设置测试环境")
        
        # 记录系统信息
        cls.system_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation()
        }
        
        logger.info(f"系统信息: {cls.system_info}")
        
        # 创建临时目录
        cls.temp_dir = tempfile.TemporaryDirectory()
        logger.info(f"创建临时目录: {cls.temp_dir.name}")
    
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        logger.info("清理测试环境")
        
        # 删除临时目录
        cls.temp_dir.cleanup()
        logger.info("临时目录已删除")
    
    def setUp(self):
        """每个测试前的准备工作"""
        # 确保Python路径正确
        self.python_exe = sys.executable
        
        # 创建临时日志文件
        self.log_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
        self.log_file.close()
        
        # 服务器进程
        self.server_process = None
    
    def tearDown(self):
        """每个测试后的清理工作"""
        # 终止服务器进程
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            logger.info("MCP服务器进程已关闭")
        
        # 输出日志文件内容
        if os.path.exists(self.log_file.name):
            with open(self.log_file.name, 'r') as f:
                logger.info(f"服务器日志内容:\n{f.read()}")
            
            # 删除临时日志文件
            os.unlink(self.log_file.name)
    
    def start_server(self, mode="websocket", host=TEST_HOST, port=TEST_PORT):
        """启动MCP服务器进程"""
        logger.info(f"启动MCP服务器进程 (模式: {mode})")
        
        # 启动服务器进程
        self.server_process = subprocess.Popen(
            [
                self.python_exe, 
                str(SERVER_SCRIPT), 
                "--mode", mode, 
                "--host", host, 
                "--port", str(port),
                "--log", self.log_file.name
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        import time
        time.sleep(2)
        logger.info(f"MCP服务器进程已启动，PID: {self.server_process.pid}")
    
    async def connect_to_server(self, host=TEST_HOST, port=TEST_PORT):
        """连接到MCP服务器"""
        uri = f"ws://{host}:{port}"
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
    
    def test_websocket_mode(self):
        """测试WebSocket模式"""
        logger.info("测试WebSocket模式")
        
        # 启动WebSocket服务器
        self.start_server(mode="websocket")
        
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 初始化
                response = await self.send_request(websocket, "initialize")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
                self.assertEqual(response["result"]["status"], "ok")
                
                # 列出工具
                response = await self.send_request(websocket, "listTools")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
                self.assertIn("tools", response["result"])
                
                # 关闭连接
                response = await self.send_request(websocket, "shutdown")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
                self.assertEqual(response["result"]["status"], "ok")
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_stdio_mode(self):
        """测试STDIO模式"""
        logger.info("测试STDIO模式")
        
        # 创建测试脚本
        test_script_path = Path(self.temp_dir.name) / "stdio_test.py"
        with open(test_script_path, "w") as f:
            f.write('''
import json
import sys
import struct

def send_message(message):
    """发送消息到STDIO服务器"""
    json_str = json.dumps(message)
    data = json_str.encode('utf-8')
    
    # 写入消息长度（4字节整数）
    sys.stdout.buffer.write(struct.pack('>I', len(data)))
    
    # 写入消息内容
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()

def receive_message():
    """从STDIO服务器接收消息"""
    # 读取消息长度（4字节整数）
    length_bytes = sys.stdin.buffer.read(4)
    length = struct.unpack('>I', length_bytes)[0]
    
    # 读取消息内容
    data = sys.stdin.buffer.read(length)
    json_str = data.decode('utf-8')
    
    return json.loads(json_str)

# 发送初始化请求
init_request = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {}
}

send_message(init_request)
init_response = receive_message()
print(json.dumps(init_response))

# 列出工具
list_request = {
    'jsonrpc': '2.0',
    'id': 2,
    'method': 'listTools',
    'params': {}
}

send_message(list_request)
list_response = receive_message()
print(json.dumps(list_response))

# 关闭连接
shutdown_request = {
    'jsonrpc': '2.0',
    'id': 3,
    'method': 'shutdown',
    'params': {}
}

send_message(shutdown_request)
shutdown_response = receive_message()
print(json.dumps(shutdown_response))
''')
        
        # 启动STDIO服务器
        server_process = subprocess.Popen(
            [
                self.python_exe, 
                str(SERVER_SCRIPT), 
                "--mode", "stdio",
                "--log", self.log_file.name
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )
        
        # 运行测试脚本
        client_process = subprocess.Popen(
            [self.python_exe, str(test_script_path)],
            stdin=server_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 获取输出
        stdout, stderr = client_process.communicate(timeout=TEST_TIMEOUT)
        
        # 终止服务器进程
        server_process.terminate()
        server_process.wait(timeout=5)
        
        # 检查输出
        logger.info(f"STDIO测试输出: {stdout}")
        if stderr:
            logger.warning(f"STDIO测试错误: {stderr}")
        
        # 解析输出
        try:
            lines = stdout.strip().split("\n")
            init_response = json.loads(lines[0])
            list_response = json.loads(lines[1])
            shutdown_response = json.loads(lines[2])
            
            # 验证响应
            self.assertEqual(init_response.get("jsonrpc"), "2.0")
            self.assertEqual(init_response.get("id"), 1)
            self.assertIn("result", init_response)
            
            self.assertEqual(list_response.get("jsonrpc"), "2.0")
            self.assertEqual(list_response.get("id"), 2)
            self.assertIn("result", list_response)
            
            self.assertEqual(shutdown_response.get("jsonrpc"), "2.0")
            self.assertEqual(shutdown_response.get("id"), 3)
            self.assertIn("result", shutdown_response)
        except Exception as e:
            logger.error(f"解析STDIO测试输出失败: {str(e)}")
            self.fail(f"STDIO测试失败: {str(e)}")
    
    def test_different_python_versions(self):
        """测试不同Python版本的兼容性"""
        logger.info("测试不同Python版本的兼容性")
        
        # 跳过实际测试，因为在单一环境中无法测试多个Python版本
        # 这里只是演示如何进行此类测试
        logger.info("此测试需要在多个Python版本环境中手动运行")
        
        # 记录当前Python版本
        logger.info(f"当前Python版本: {platform.python_version()}")
        
        # 在实际测试中，可以使用不同版本的Python解释器启动服务器
        # 并验证客户端是否可以正常连接和通信
    
    def test_different_platforms(self):
        """测试不同平台的兼容性"""
        logger.info("测试不同平台的兼容性")
        
        # 跳过实际测试，因为在单一平台中无法测试多个平台
        # 这里只是演示如何进行此类测试
        logger.info("此测试需要在多个平台环境中手动运行")
        
        # 记录当前平台
        logger.info(f"当前平台: {platform.system()} {platform.release()}")
        
        # 在实际测试中，可以在不同平台上运行相同的测试
        # 并验证服务器和客户端是否可以正常工作
    
    def test_protocol_compliance(self):
        """测试协议兼容性"""
        logger.info("测试协议兼容性")
        
        # 启动WebSocket服务器
        self.start_server(mode="websocket")
        
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 测试标准JSON-RPC请求
                response = await self.send_request(websocket, "initialize")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
                
                # 测试无效JSON-RPC请求
                await websocket.send("{invalid json}")
                response_text = await websocket.recv()
                response = json.loads(response_text)
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertIn("error", response)
                self.assertEqual(response["error"]["code"], -32700)  # 解析错误
                
                # 测试缺少必需字段的请求
                await websocket.send(json.dumps({"method": "initialize"}))
                response_text = await websocket.recv()
                response = json.loads(response_text)
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertIn("error", response)
                self.assertEqual(response["error"]["code"], -32600)  # 无效请求
                
                # 测试批量请求（如果支持）
                batch_request = [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    {"jsonrpc": "2.0", "id": 2, "method": "listTools", "params": {}}
                ]
                await websocket.send(json.dumps(batch_request))
                
                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=2)
                    response = json.loads(response_text)
                    logger.info(f"批量请求响应: {response}")
                    # 注意：MCP协议可能不支持批量请求，所以这里不做断言
                except asyncio.TimeoutError:
                    logger.info("批量请求超时，可能不支持批量请求")
                
                # 关闭连接
                response = await self.send_request(websocket, "shutdown")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
            finally:
                await websocket.close()
        
        asyncio.run(run_test())
    
    def test_error_handling(self):
        """测试错误处理"""
        logger.info("测试错误处理")
        
        # 启动WebSocket服务器
        self.start_server(mode="websocket")
        
        async def run_test():
            websocket = await self.connect_to_server()
            try:
                # 测试方法不存在
                response = await self.send_request(websocket, "nonExistentMethod")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("error", response)
                self.assertEqual(response["error"]["code"], -32601)  # 方法不存在
                
                # 测试无效参数
                response = await self.send_request(websocket, "initialize", {"invalidParam": "value"})
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                # 注意：initialize可能不检查参数，所以这里不断言错误代码
                
                # 测试调用不存在的工具
                response = await self.send_request(websocket, "callTool", {
                    "name": "nonExistentTool",
                    "params": {}
                })
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("error", response)
                
                # 关闭连接
                response = await self.send_request(websocket, "shutdown")
                self.assertEqual(response.get("jsonrpc"), "2.0")
                self.assertEqual(response.get("id"), 1)
                self.assertIn("result", response)
            finally:
                await websocket.close()
        
        asyncio.run(run_test())


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP服务器兼容性测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    unittest.main(argv=['first-arg-is-ignored'], exit=False)


if __name__ == "__main__":
    main() 