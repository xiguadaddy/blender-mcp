#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BlenderMCP MCP服务器压力测试
"""

import asyncio
import json
import os
import sys
import time
import random
import websockets
import tempfile
import subprocess
import logging
import argparse
import psutil
from pathlib import Path
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_stress_test")

# 测试配置
TEST_HOST = "localhost"
TEST_PORT = 9879  # 使用不同于默认端口的端口，避免冲突
TEST_TIMEOUT = 60  # 超时时间（秒）

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
SERVER_SCRIPT = PROJECT_ROOT / "src" / "blendermcp" / "server" / "run_mcp_server.py"


class MCPStressTest:
    """MCP服务器压力测试类"""
    
    def __init__(self, max_clients=100, test_duration=60, ramp_up_time=10, request_interval=0.5):
        """初始化压力测试"""
        self.max_clients = max_clients
        self.test_duration = test_duration
        self.ramp_up_time = ramp_up_time
        self.request_interval = request_interval
        self.server_process = None
        self.log_file = None
        self.start_time = None
        self.end_time = None
        self.active_clients = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.server_metrics = []
        self.stop_event = asyncio.Event()
    
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
        # 计算客户端启动延迟，实现渐进式增加负载
        if self.ramp_up_time > 0:
            delay = (client_id / self.max_clients) * self.ramp_up_time
            await asyncio.sleep(delay)
        
        logger.debug(f"客户端 {client_id} 开始测试")
        self.active_clients += 1
        
        try:
            websocket = await self.connect_to_server()
        except Exception as e:
            logger.error(f"客户端 {client_id} 连接失败: {str(e)}")
            self.active_clients -= 1
            self.failed_requests += 1
            return
        
        try:
            # 初始化
            try:
                response, duration = await self.send_request(websocket, "initialize")
                self.total_requests += 1
                if "result" in response:
                    self.successful_requests += 1
                    self.response_times.append(duration)
                else:
                    self.failed_requests += 1
            except Exception as e:
                logger.error(f"客户端 {client_id} 初始化失败: {str(e)}")
                self.total_requests += 1
                self.failed_requests += 1
            
            # 列出工具
            try:
                tools_response, duration = await self.send_request(websocket, "listTools")
                self.total_requests += 1
                if "result" in tools_response:
                    self.successful_requests += 1
                    self.response_times.append(duration)
                    tools = tools_response.get("result", {}).get("tools", [])
                else:
                    self.failed_requests += 1
                    tools = []
            except Exception as e:
                logger.error(f"客户端 {client_id} 列出工具失败: {str(e)}")
                self.total_requests += 1
                self.failed_requests += 1
                tools = []
            
            # 持续发送请求，直到测试结束
            while not self.stop_event.is_set():
                try:
                    # 随机选择一个方法
                    method = random.choice(["listTools", "callTool"])
                    
                    if method == "callTool" and tools:
                        # 随机选择一个工具
                        tool = random.choice(tools)
                        tool_name = tool["name"]
                        
                        # 调用工具
                        response, duration = await self.send_request(websocket, "callTool", {
                            "name": tool_name,
                            "params": {}
                        })
                    else:
                        # 列出工具
                        response, duration = await self.send_request(websocket, "listTools")
                    
                    self.total_requests += 1
                    if "result" in response:
                        self.successful_requests += 1
                        self.response_times.append(duration)
                    else:
                        self.failed_requests += 1
                
                except Exception as e:
                    logger.error(f"客户端 {client_id} 请求失败: {str(e)}")
                    self.total_requests += 1
                    self.failed_requests += 1
                
                # 等待一段时间再发送下一个请求
                await asyncio.sleep(self.request_interval * (0.5 + random.random()))
            
            # 关闭连接
            try:
                response, duration = await self.send_request(websocket, "shutdown")
                self.total_requests += 1
                if "result" in response:
                    self.successful_requests += 1
                    self.response_times.append(duration)
                else:
                    self.failed_requests += 1
            except Exception as e:
                logger.error(f"客户端 {client_id} 关闭失败: {str(e)}")
                self.total_requests += 1
                self.failed_requests += 1
            
            logger.debug(f"客户端 {client_id} 完成测试")
        
        except Exception as e:
            logger.error(f"客户端 {client_id} 会话错误: {str(e)}")
        
        finally:
            try:
                await websocket.close()
            except:
                pass
            self.active_clients -= 1
    
    async def monitor_server(self):
        """监控服务器资源使用情况"""
        while not self.stop_event.is_set():
            if self.server_process:
                try:
                    # 获取进程信息
                    process = psutil.Process(self.server_process.pid)
                    
                    # 收集指标
                    cpu_percent = process.cpu_percent(interval=1)
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)  # 转换为MB
                    
                    # 记录指标
                    self.server_metrics.append({
                        "timestamp": datetime.now().isoformat(),
                        "active_clients": self.active_clients,
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb,
                        "total_requests": self.total_requests,
                        "successful_requests": self.successful_requests,
                        "failed_requests": self.failed_requests
                    })
                    
                    logger.info(f"服务器指标 - 活动客户端: {self.active_clients}, CPU: {cpu_percent:.1f}%, "
                                f"内存: {memory_mb:.1f}MB, 请求: {self.total_requests}")
                
                except Exception as e:
                    logger.error(f"监控服务器失败: {str(e)}")
            
            # 每秒更新一次
            await asyncio.sleep(1)
    
    async def run_stress_test(self):
        """运行压力测试"""
        logger.info(f"开始压力测试: 最大 {self.max_clients} 客户端, 持续 {self.test_duration} 秒")
        
        self.start_time = datetime.now()
        
        # 启动监控任务
        monitor_task = asyncio.create_task(self.monitor_server())
        
        # 创建客户端任务
        client_tasks = [asyncio.create_task(self.client_session(i)) for i in range(self.max_clients)]
        
        # 等待测试持续时间
        await asyncio.sleep(self.test_duration)
        
        # 设置停止事件，通知所有客户端停止
        self.stop_event.set()
        
        # 等待所有客户端完成
        await asyncio.gather(*client_tasks)
        
        # 取消监控任务
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        self.end_time = datetime.now()
        
        # 分析结果
        self.analyze_results()
    
    def analyze_results(self):
        """分析测试结果"""
        logger.info("压力测试结果:")
        
        # 计算测试持续时间
        duration = (self.end_time - self.start_time).total_seconds()
        
        # 计算请求统计
        total_requests = self.total_requests
        successful_requests = self.successful_requests
        failed_requests = self.failed_requests
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        # 计算吞吐量
        throughput = total_requests / duration
        
        logger.info(f"测试持续时间: {duration:.2f} 秒")
        logger.info(f"总请求数: {total_requests}")
        logger.info(f"成功请求数: {successful_requests}")
        logger.info(f"失败请求数: {failed_requests}")
        logger.info(f"成功率: {success_rate:.2f}%")
        logger.info(f"吞吐量: {throughput:.2f} 请求/秒")
        
        # 响应时间统计
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            min_response_time = min(self.response_times)
            max_response_time = max(self.response_times)
            sorted_times = sorted(self.response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.5)]
            p90 = sorted_times[int(len(sorted_times) * 0.9)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            
            logger.info(f"平均响应时间: {avg_response_time:.2f} ms")
            logger.info(f"最小响应时间: {min_response_time:.2f} ms")
            logger.info(f"最大响应时间: {max_response_time:.2f} ms")
            logger.info(f"中位数响应时间 (P50): {p50:.2f} ms")
            logger.info(f"P90 响应时间: {p90:.2f} ms")
            logger.info(f"P95 响应时间: {p95:.2f} ms")
            logger.info(f"P99 响应时间: {p99:.2f} ms")
        
        # 服务器资源使用统计
        if self.server_metrics:
            cpu_values = [m["cpu_percent"] for m in self.server_metrics]
            memory_values = [m["memory_mb"] for m in self.server_metrics]
            
            avg_cpu = sum(cpu_values) / len(cpu_values)
            max_cpu = max(cpu_values)
            avg_memory = sum(memory_values) / len(memory_values)
            max_memory = max(memory_values)
            
            logger.info(f"平均CPU使用率: {avg_cpu:.2f}%")
            logger.info(f"最大CPU使用率: {max_cpu:.2f}%")
            logger.info(f"平均内存使用: {avg_memory:.2f} MB")
            logger.info(f"最大内存使用: {max_memory:.2f} MB")
        
        # 保存详细结果到文件
        self.save_results()
    
    def save_results(self):
        """保存测试结果到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = PROJECT_ROOT / "tests" / "results"
        results_dir.mkdir(exist_ok=True)
        
        # 保存摘要结果
        summary_file = results_dir / f"stress_test_summary_{timestamp}.txt"
        with open(summary_file, "w") as f:
            f.write(f"MCP服务器压力测试结果 - {datetime.now().isoformat()}\n")
            f.write(f"测试配置:\n")
            f.write(f"  最大客户端数: {self.max_clients}\n")
            f.write(f"  测试持续时间: {self.test_duration} 秒\n")
            f.write(f"  渐进增加时间: {self.ramp_up_time} 秒\n")
            f.write(f"  请求间隔: {self.request_interval} 秒\n\n")
            
            duration = (self.end_time - self.start_time).total_seconds()
            f.write(f"测试持续时间: {duration:.2f} 秒\n")
            f.write(f"总请求数: {self.total_requests}\n")
            f.write(f"成功请求数: {self.successful_requests}\n")
            f.write(f"失败请求数: {self.failed_requests}\n")
            success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
            f.write(f"成功率: {success_rate:.2f}%\n")
            throughput = self.total_requests / duration
            f.write(f"吞吐量: {throughput:.2f} 请求/秒\n\n")
            
            if self.response_times:
                avg_response_time = sum(self.response_times) / len(self.response_times)
                min_response_time = min(self.response_times)
                max_response_time = max(self.response_times)
                sorted_times = sorted(self.response_times)
                p50 = sorted_times[int(len(sorted_times) * 0.5)]
                p90 = sorted_times[int(len(sorted_times) * 0.9)]
                p95 = sorted_times[int(len(sorted_times) * 0.95)]
                p99 = sorted_times[int(len(sorted_times) * 0.99)]
                
                f.write(f"响应时间统计:\n")
                f.write(f"  平均响应时间: {avg_response_time:.2f} ms\n")
                f.write(f"  最小响应时间: {min_response_time:.2f} ms\n")
                f.write(f"  最大响应时间: {max_response_time:.2f} ms\n")
                f.write(f"  中位数响应时间 (P50): {p50:.2f} ms\n")
                f.write(f"  P90 响应时间: {p90:.2f} ms\n")
                f.write(f"  P95 响应时间: {p95:.2f} ms\n")
                f.write(f"  P99 响应时间: {p99:.2f} ms\n\n")
            
            if self.server_metrics:
                cpu_values = [m["cpu_percent"] for m in self.server_metrics]
                memory_values = [m["memory_mb"] for m in self.server_metrics]
                
                avg_cpu = sum(cpu_values) / len(cpu_values)
                max_cpu = max(cpu_values)
                avg_memory = sum(memory_values) / len(memory_values)
                max_memory = max(memory_values)
                
                f.write(f"服务器资源使用统计:\n")
                f.write(f"  平均CPU使用率: {avg_cpu:.2f}%\n")
                f.write(f"  最大CPU使用率: {max_cpu:.2f}%\n")
                f.write(f"  平均内存使用: {avg_memory:.2f} MB\n")
                f.write(f"  最大内存使用: {max_memory:.2f} MB\n")
        
        logger.info(f"测试摘要已保存到 {summary_file}")
        
        # 保存详细指标
        metrics_file = results_dir / f"stress_test_metrics_{timestamp}.csv"
        with open(metrics_file, "w") as f:
            f.write("timestamp,active_clients,cpu_percent,memory_mb,total_requests,successful_requests,failed_requests\n")
            for metric in self.server_metrics:
                f.write(f"{metric['timestamp']},{metric['active_clients']},{metric['cpu_percent']:.2f},"
                        f"{metric['memory_mb']:.2f},{metric['total_requests']},{metric['successful_requests']},"
                        f"{metric['failed_requests']}\n")
        
        logger.info(f"详细指标已保存到 {metrics_file}")
    
    def run(self):
        """运行完整的压力测试"""
        try:
            self.start_server()
            asyncio.run(self.run_stress_test())
        finally:
            self.stop_server()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP服务器压力测试")
    parser.add_argument("--clients", type=int, default=100, help="最大客户端数量")
    parser.add_argument("--duration", type=int, default=60, help="测试持续时间（秒）")
    parser.add_argument("--ramp-up", type=int, default=10, help="渐进增加时间（秒）")
    parser.add_argument("--interval", type=float, default=0.5, help="请求间隔（秒）")
    args = parser.parse_args()
    
    test = MCPStressTest(
        max_clients=args.clients,
        test_duration=args.duration,
        ramp_up_time=args.ramp_up,
        request_interval=args.interval
    )
    test.run()


if __name__ == "__main__":
    main() 