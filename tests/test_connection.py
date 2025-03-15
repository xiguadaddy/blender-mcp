"""BlenderMCP连接池测试模块"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from blendermcp.client.connection import ConnectionPool, ConnectionInfo

@pytest.fixture
async def pool():
    """创建测试连接池"""
    pool = ConnectionPool(
        host="localhost",
        port=9876,
        max_size=5,
        min_size=2,
        max_lifetime=60,
        max_idle_time=30
    )
    yield pool
    await pool.stop()

@pytest.mark.asyncio
async def test_pool_initialization(pool):
    """测试连接池初始化"""
    assert pool.host == "localhost"
    assert pool.port == 9876
    assert pool.max_size == 5
    assert pool.min_size == 2
    assert pool.max_lifetime == timedelta(seconds=60)
    assert pool.max_idle_time == timedelta(seconds=30)
    assert len(pool._pool) == 0

@pytest.mark.asyncio
async def test_pool_start_stop():
    """测试连接池启动和停止"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_connect.return_value = mock_ws
        
        pool = ConnectionPool("localhost", 9876, min_size=2)
        await pool.start()
        
        # 验证创建了最小数量的连接
        assert len(pool._pool) == 2
        assert mock_connect.call_count == 2
        
        # 停止连接池
        await pool.stop()
        assert len(pool._pool) == 0
        assert mock_ws.close.call_count == 2

@pytest.mark.asyncio
async def test_get_connection(pool):
    """测试获取连接"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_connect.return_value = mock_ws
        
        await pool.start()
        
        # 获取连接
        conn1 = await pool.get_connection()
        assert conn1 is not None
        
        # 验证连接状态
        for info in pool._pool.values():
            if info.connection == conn1:
                assert info.is_busy
                break
        else:
            assert False, "未找到连接信息"
            
        # 释放连接
        await pool.release_connection(conn1)
        
        # 验证连接已释放
        for info in pool._pool.values():
            if info.connection == conn1:
                assert not info.is_busy
                break

@pytest.mark.asyncio
async def test_connection_limit(pool):
    """测试连接数限制"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_connect.return_value = mock_ws
        
        await pool.start()
        
        # 获取最大数量的连接
        connections = []
        for _ in range(pool.max_size):
            conn = await pool.get_connection()
            connections.append(conn)
            
        # 验证连接数
        assert len(pool._pool) == pool.max_size
        
        # 尝试获取更多连接应该等待
        get_more = asyncio.create_task(pool.get_connection())
        await asyncio.sleep(0.1)
        assert not get_more.done()
        
        # 释放一个连接
        await pool.release_connection(connections[0])
        
        # 现在应该能获取到连接
        conn = await get_more
        assert conn is not None

@pytest.mark.asyncio
async def test_connection_maintenance(pool):
    """测试连接维护"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_connect.return_value = mock_ws
        
        await pool.start()
        
        # 模拟一个过期连接
        conn_id = list(pool._pool.keys())[0]
        info = pool._pool[conn_id]
        info.created_at = datetime.now() - timedelta(seconds=pool.max_lifetime.seconds + 10)
        
        # 运行维护任务
        await pool._maintain_pool()
        
        # 验证过期连接被关闭并创建了新连接
        assert conn_id not in pool._pool
        assert len(pool._pool) == pool.min_size

@pytest.mark.asyncio
async def test_connection_error_handling(pool):
    """测试连接错误处理"""
    with patch("websockets.connect") as mock_connect:
        # 模拟连接失败
        mock_connect.side_effect = Exception("连接失败")
        
        # 尝试启动连接池应该失败
        with pytest.raises(ConnectionError):
            await pool.start()
            
        # 验证重试机制
        assert mock_connect.call_count == pool.retry_limit * pool.min_size

@pytest.mark.asyncio
async def test_get_stats(pool):
    """测试获取统计信息"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_connect.return_value = mock_ws
        
        await pool.start()
        
        # 获取一些连接
        conn1 = await pool.get_connection()
        conn2 = await pool.get_connection()
        
        # 验证统计信息
        stats = pool.get_stats()
        assert stats["total_connections"] == pool.min_size
        assert stats["busy_connections"] == 2
        assert stats["idle_connections"] == pool.min_size - 2 