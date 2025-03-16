#!/usr/bin/env python
"""
BlenderMCP服务启动脚本

使用方法:
1. 先启动Blender并加载BlenderMCP插件
2. 在Blender中启动MCP监听器
3. 在单独的终端中运行此脚本，启动MCP服务器核心

此脚本将启动独立的MCP服务器进程，该进程不依赖bpy，
并通过IPC与Blender插件通信来执行Blender操作。
"""

import os
import sys
import subprocess
import argparse
import tempfile
import time
import socket
from pathlib import Path

def is_port_in_use(port, host='127.0.0.1'):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except socket.error:
            return True
        return False

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="启动BlenderMCP服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听主机地址")
    parser.add_argument("--port", type=int, default=5000, help="监听端口")
    parser.add_argument("--mode", choices=["websocket", "stdio", "http"], default="websocket", 
                        help="服务模式: websocket, stdio 或 http")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    
    # 检查端口是否被占用
    if is_port_in_use(args.port, args.host):
        print(f"错误: 端口 {args.port} 已被占用，请选择其他端口。")
        return 1
    
    # 获取当前脚本的路径
    script_dir = Path(__file__).resolve().parent
    
    # 确定BlenderMCP包路径和服务器脚本路径
    package_dir = script_dir.parent.parent  # 上两级目录
    server_script = os.path.join(script_dir.parent, "server", "run_mcp_server_simple.py")
    
    # 如果服务器脚本不存在，尝试备用路径
    if not os.path.exists(server_script):
        server_script = os.path.join(script_dir.parent, "server", "run_mcp_server.py")
        
    if not os.path.exists(server_script):
        print(f"错误: 找不到服务器脚本 run_mcp_server.py 或 run_mcp_server_simple.py")
        return 1
    
    # 使用当前Python解释器
    python_path = sys.executable
    
    # 构建命令行
    cmd = [
        python_path,
        server_script,
        "--host", args.host,
        "--port", str(args.port),
        "--mode", args.mode
    ]
    
    if args.debug:
        cmd.append("--debug")
    
    # 设置环境变量
    env = os.environ.copy()
    
    # 将包路径添加到PYTHONPATH
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{package_dir}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = str(package_dir)
    
    print("=" * 60)
    print("BlenderMCP服务启动程序")
    print("=" * 60)
    print(f"启动MCP服务器，运行模式: {args.mode}")
    print(f"监听地址: {args.host}:{args.port}")
    print(f"服务器脚本: {server_script}")
    print(f"Python解释器: {python_path}")
    print(f"PYTHONPATH: {env.get('PYTHONPATH', '')}")
    print(f"命令: {' '.join(cmd)}")
    print()
    print("使用方法:")
    print("1. 确保Blender已经启动并加载BlenderMCP插件")
    print("2. 在Blender中启动MCP监听器")
    print("3. 等待MCP服务器连接到Blender")
    print("4. 使用MCP客户端连接到MCP服务器")
    print("=" * 60)
    
    # 启动服务器进程
    try:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 创建状态文件以指示服务器正在运行
        status_file = Path(tempfile.gettempdir()) / "blendermcp_server_status.json"
        with open(status_file, "w") as f:
            import json
            json.dump({
                "pid": process.pid,
                "host": args.host,
                "port": args.port,
                "mode": args.mode,
                "start_time": time.time()
            }, f)
        
        print(f"服务器进程已启动，PID: {process.pid}")
        print(f"状态文件已创建: {status_file}")
        
        # 实时输出日志
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line.rstrip())
        
        # 检查返回码
        returncode = process.poll()
        if returncode != 0:
            print(f"服务器进程异常退出，返回码: {returncode}")
            return returncode
            
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在关闭服务器...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("服务器已关闭")
        
        # 清除状态文件
        if status_file.exists():
            status_file.unlink()
    except Exception as e:
        print(f"启动服务器时出错: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 