#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BlenderMCP MCP服务器性能测试
"""

import asyncio
import json
import os
import sys
import time
import statistics
import websockets
import tempfile
import subprocess
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_performance_test")

# 测试配置
TEST_HOST = "localhost"
TEST_PORT = 9878  # 使用不同于默认端口的端口，避免冲突
TEST_TIMEOUT = 30  # 超时时间（秒）

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
SERVER_SCRIPT = PROJECT_ROOT / "src" / "blendermcp" / "server" / "run_mcp_server.py"


class MCPPerformanceTest:
    """MCP服务器性能测试类"""
    
    def __init__(self, concurrent_clients=10, requests_per_client=50, warmup_requests=5):
        """初始化性能测试"""
        self.concurrent_clients = concurrent_clients
        self.requests_per_client = requests_per_client
        self.warmup_requests = warmup_requests
        self.server_process = None
        self.log_file = None
        self.results = {
            "initialize": [],
            "listTools": [],
            "callTool": [],
            "shutdown": []
        }
    
    def start_server(self):
        """启动MCP服务器进程"""
        logger.info("启动MCP服务器进程")
        
        # 确保Python路径正确
        python_exe = sys.executable
        
        # 创建临时日志文件
        self.log_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
        self.log_file.close()
        
        # 启动服务器进程
        self.server_process = subprocess.Popen(
            [
                python_exe, 
                str(SERVER_SCRIPT), 
                "--mode", "websocket", 
                "--host", TEST_HOST, 
                "--port", str(TEST_PORT),
                "--log", self.log_file.name
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        time.sleep(2)
        logger.info(f"MCP服务器进程已启动，PID: {self.server_process.pid}")
    
    def stop_server(self):
        """关闭MCP服务器进程"""
        logger.info("关闭MCP服务器进程")
        
        # 终止服务器进程
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            logger.info("MCP服务器进程已关闭")
        
        # 输出日志文件内容
        if self.log_file and os.path.exists(self.log_file.name):
            # 删除临时日志文件
            os.unlink(self.log_file.name)
    
    async def connect_to_server(self):
        """连接到MCP服务器"""
        uri = f"ws://{TEST_HOST}:{TEST_PORT}"
        return await websockets.connect(uri)
    
    async def send_request(self, websocket, method, params=None):
        """发送JSON-RPC请求并测量响应时间"""
        if params is None:
            params = {}
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        start_time = time.time()
        await websocket.send(json.dumps(request))
        response_text = await websocket.recv()
        end_time = time.time()
        
        response = json.loads(response_text)
        duration_ms = (end_time - start_time) * 1000  # 转换为毫秒
        
        return response, duration_ms
    
    async def client_session(self, client_id):
        """单个客户端会话"""
        logger.info(f"客户端 {client_id} 开始测试")
        
        websocket = await self.connect_to_server()
        try:
            client_results = {
                "initialize": [],
                "listTools": [],
                "callTool": [],
                "shutdown": []
            }
            
            # 预热请求
            for _ in range(self.warmup_requests):
                await self.send_request(websocket, "initialize")
                await self.send_request(websocket, "listTools")
            
            # 初始化请求
            _, duration = await self.send_request(websocket, "initialize")
            client_results["initialize"].append(duration)
            
            # 列出工具请求
            tools_response, duration = await self.send_request(websocket, "listTools")
            client_results["listTools"].append(duration)
            
            # 获取第一个工具
            tools = tools_response.get("result", {}).get("tools", [])
            if tools:
                first_tool = tools[0]
                tool_name = first_tool["name"]
                
                # 调用工具请求
                for _ in range(self.requests_per_client):
                    _, duration = await self.send_request(websocket, "callTool", {
                        "name": tool_name,
                        "params": {}
                    })
                    client_results["callTool"].append(duration)
            
            # 关闭请求
            _, duration = await self.send_request(websocket, "shutdown")
            client_results["shutdown"].append(duration)
            
            logger.info(f"客户端 {client_id} 完成测试")
            return client_results
            
        finally:
            await websocket.close()
    
    async def run_performance_test(self):
        """运行性能测试"""
        logger.info(f"开始性能测试: {self.concurrent_clients} 并发客户端, 每个客户端 {self.requests_per_client} 请求")
        
        # 创建并发客户端
        tasks = [self.client_session(i) for i in range(self.concurrent_clients)]
        client_results = await asyncio.gather(*tasks)
        
        # 合并结果
        for client_result in client_results:
            for method, durations in client_result.items():
                self.results[method].extend(durations)
        
        # 分析结果
        self.analyze_results()
    
    def analyze_results(self):
        """分析测试结果"""
        logger.info("性能测试结果:")
        
        for method, durations in self.results.items():
            if durations:
                avg = statistics.mean(durations)
                median = statistics.median(durations)
                p95 = sorted(durations)[int(len(durations) * 0.95)]
                p99 = sorted(durations)[int(len(durations) * 0.99)]
                min_val = min(durations)
                max_val = max(durations)
                
                logger.info(f"方法: {method}")
                logger.info(f"  样本数: {len(durations)}")
                logger.info(f"  平均响应时间: {avg:.2f} ms")
                logger.info(f"  中位数响应时间: {median:.2f} ms")
                logger.info(f"  95%响应时间: {p95:.2f} ms")
                logger.info(f"  99%响应时间: {p99:.2f} ms")
                logger.info(f"  最小响应时间: {min_val:.2f} ms")
                logger.info(f"  最大响应时间: {max_val:.2f} ms")
                logger.info("")
    
    def run(self):
        """运行完整的性能测试"""
        try:
            self.start_server()
            asyncio.run(self.run_performance_test())
        finally:
            self.stop_server()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP服务器性能测试")
    parser.add_argument("--clients", type=int, default=10, help="并发客户端数量")
    parser.add_argument("--requests", type=int, default=50, help="每个客户端的请求数量")
    parser.add_argument("--warmup", type=int, default=5, help="预热请求数量")
    args = parser.parse_args()
    
    test = MCPPerformanceTest(
        concurrent_clients=args.clients,
        requests_per_client=args.requests,
        warmup_requests=args.warmup
    )
    test.run()


if __name__ == "__main__":
    main() 