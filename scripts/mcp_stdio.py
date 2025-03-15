#!/usr/bin/env python
"""MCP标准输入/输出模式启动脚本"""

import asyncio
import os
import sys
import logging

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.blendermcp.mcp import MCPServer

# 配置基本日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='blendermcp_mcp.log',  # 输出到文件便于调试
    filemode='a'
)

async def main():
    """启动MCP服务器（仅标准输入/输出模式）"""
    server = MCPServer()
    await server.start_stdio()

if __name__ == "__main__":
    asyncio.run(main())
