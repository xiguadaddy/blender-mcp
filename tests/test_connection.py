"""
测试连接池管理模块
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from blendermcp.client.connection import ConnectionPool

@pytest.mark.asyncio
class TestConnectionPool:
    """测试连接池"""
    
    async def test_get_connection(self, websocket_url):
        """测试获取连接"""
        pool = ConnectionPool(max_connections=2)
        
        # 获取第一个连接
        conn1 = await pool.get_connection(websocket_url)
        assert not conn1.closed
        assert len(pool.connections) == 1
        
        # 获取第二个连接
        conn2 = await pool.get_connection(websocket_url)
        assert not conn2.closed
        assert len(pool.connections) == 2
        
        # 获取第三个连接(应该关闭最旧的连接)
        conn3 = await pool.get_connection(websocket_url)
        assert not conn3.closed
        assert len(pool.connections) == 2
        
        await pool.close_all()
        
    async def test_connection_reuse(self, websocket_url):
        """测试连接重用"""
        pool = ConnectionPool()
        
        # 获取连接
        conn1 = await pool.get_connection(websocket_url)
        conn_id1 = str(id(conn1))
        
        # 再次获取相同URL的连接
        conn2 = await pool.get_connection(websocket_url)
        conn_id2 = str(id(conn2))
        
        # 应该返回相同的连接
        assert conn_id1 == conn_id2
        assert len(pool.connections) == 1
        
        await pool.close_all()
        
    async def test_cleanup_expired(self, websocket_url):
        """测试清理过期连接"""
        pool = ConnectionPool(timeout=1)  # 1秒超时
        
        # 获取连接
        conn = await pool.get_connection(websocket_url)
        assert len(pool.connections) == 1
        
        # 等待超时
        await asyncio.sleep(1.1)
        
        # 清理过期连接
        await pool._cleanup_expired()
        assert len(pool.connections) == 0
        
    async def test_close_connection(self, websocket_url):
        """测试关闭连接"""
        pool = ConnectionPool()
        
        # 获取连接
        conn = await pool.get_connection(websocket_url)
        conn_id = str(id(conn))
        assert len(pool.connections) == 1
        
        # 关闭连接
        await pool.close_connection(conn_id)
        assert len(pool.connections) == 0
        assert conn.closed
        
    async def test_cleanup_task(self, websocket_url):
        """测试清理任务"""
        pool = ConnectionPool(timeout=1)
        
        # 启动清理任务
        pool.start_cleanup_task()
        
        # 获取连接
        conn = await pool.get_connection(websocket_url)
        assert len(pool.connections) == 1
        
        # 等待清理任务运行
        await asyncio.sleep(1.2)
        assert len(pool.connections) == 0
        
        # 停止清理任务
        pool.stop_cleanup_task()
        await pool.close_all() 