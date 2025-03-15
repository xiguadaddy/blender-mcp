"""
测试配置文件
"""

import os
import sys
import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# 添加模拟模块
sys.modules['bpy'] = __import__('tests.mock_bpy', fromlist=['*'])

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def websocket_url():
    """WebSocket服务器URL"""
    return "ws://localhost:9876"

@pytest.fixture
async def connection_pool():
    """创建连接池"""
    from blendermcp.client.connection import ConnectionPool
    pool = ConnectionPool(max_connections=2, timeout=1)
    yield pool
    await pool.close_all() 