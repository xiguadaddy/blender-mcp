#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BlenderMCP 测试运行脚本
"""

import os
import sys
import unittest
import argparse
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_runner")

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


def discover_tests(test_type=None):
    """发现测试用例"""
    test_dir = PROJECT_ROOT / "tests"
    
    if test_type:
        # 运行特定类型的测试
        if test_type == "integration":
            test_dir = test_dir / "integration"
        elif test_type == "performance":
            test_dir = test_dir / "performance"
        elif test_type == "stress":
            test_dir = test_dir / "stress"
        elif test_type == "compatibility":
            test_dir = test_dir / "compatibility"
        else:
            logger.warning(f"未知的测试类型: {test_type}，将运行所有测试")
    
    logger.info(f"从目录 {test_dir} 发现测试")
    return unittest.defaultTestLoader.discover(test_dir, pattern="test_*.py")


def run_tests(test_suite, verbosity=1):
    """运行测试套件"""
    logger.info("开始运行测试")
    
    # 创建测试结果目录
    results_dir = PROJECT_ROOT / "tests" / "results"
    results_dir.mkdir(exist_ok=True)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(test_suite)
    
    # 输出测试结果
    logger.info(f"测试完成: 运行 {result.testsRun} 个测试")
    logger.info(f"成功: {result.testsRun - len(result.errors) - len(result.failures)}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    
    # 返回测试结果
    return result


def run_performance_tests(clients=10, requests=50, warmup=5):
    """运行性能测试"""
    logger.info("运行性能测试")
    
    # 导入性能测试模块
    sys.path.append(str(PROJECT_ROOT))
    from tests.performance.test_mcp_performance import MCPPerformanceTest
    
    # 创建并运行性能测试
    test = MCPPerformanceTest(
        concurrent_clients=clients,
        requests_per_client=requests,
        warmup_requests=warmup
    )
    test.run()


def run_stress_tests(clients=100, duration=60, ramp_up=10, interval=0.5):
    """运行压力测试"""
    logger.info("运行压力测试")
    
    # 导入压力测试模块
    sys.path.append(str(PROJECT_ROOT))
    from tests.stress.test_mcp_stress import MCPStressTest
    
    # 创建并运行压力测试
    test = MCPStressTest(
        max_clients=clients,
        test_duration=duration,
        ramp_up_time=ramp_up,
        request_interval=interval
    )
    test.run()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="BlenderMCP 测试运行脚本")
    parser.add_argument("--type", choices=["integration", "performance", "stress", "compatibility", "all"], 
                        default="all", help="要运行的测试类型")
    parser.add_argument("--verbose", "-v", action="count", default=1, help="详细程度")
    
    # 性能测试参数
    parser.add_argument("--clients", type=int, default=10, help="性能/压力测试的并发客户端数量")
    parser.add_argument("--requests", type=int, default=50, help="性能测试中每个客户端的请求数量")
    parser.add_argument("--warmup", type=int, default=5, help="性能测试的预热请求数量")
    
    # 压力测试参数
    parser.add_argument("--duration", type=int, default=60, help="压力测试持续时间（秒）")
    parser.add_argument("--ramp-up", type=int, default=10, help="压力测试渐进增加时间（秒）")
    parser.add_argument("--interval", type=float, default=0.5, help="压力测试请求间隔（秒）")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 运行测试
    if args.type == "performance":
        run_performance_tests(
            clients=args.clients,
            requests=args.requests,
            warmup=args.warmup
        )
    elif args.type == "stress":
        run_stress_tests(
            clients=args.clients,
            duration=args.duration,
            ramp_up=args.ramp_up,
            interval=args.interval
        )
    else:
        # 运行单元测试和集成测试
        test_suite = discover_tests(args.type if args.type != "all" else None)
        result = run_tests(test_suite, verbosity=args.verbose)
        
        # 设置退出代码
        if len(result.errors) > 0 or len(result.failures) > 0:
            sys.exit(1)


if __name__ == "__main__":
    main() 