"""BlenderMCP连接池管理模块"""

import asyncio
import logging
from websockets.asyncio.client import connect, ClientConnection
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """连接信息"""
    connection: ClientConnection
    created_at: datetime
    last_used: datetime
    is_busy: bool = False
    error_count: int = 0

class ConnectionPool:
    """WebSocket连接池管理器"""
    
    def __init__(
        self,
        host: str,
        port: int,
        max_size: int = 10,
        min_size: int = 2,
        max_lifetime: int = 3600,
        max_idle_time: int = 300,
        retry_limit: int = 3
    ):
        """初始化连接池
        
        Args:
            host: 服务器主机
            port: 服务器端口
            max_size: 最大连接数
            min_size: 最小连接数
            max_lifetime: 连接最大生命周期(秒)
            max_idle_time: 最大空闲时间(秒)
            retry_limit: 重试次数限制
        """
        self.host = host
        self.port = port
        self.max_size = max_size
        self.min_size = min_size
        self.max_lifetime = timedelta(seconds=max_lifetime)
        self.max_idle_time = timedelta(seconds=max_idle_time)
        self.retry_limit = retry_limit
        
        self._pool: Dict[str, ConnectionInfo] = {}
        self._lock = asyncio.Lock()
        self._maintenance_task = None
        
    async def start(self):
        """启动连接池"""
        # 创建初始连接
        async with self._lock:
            for _ in range(self.min_size):
                await self._create_connection()
                
        # 启动维护任务
        self._maintenance_task = asyncio.create_task(self._maintain_pool())
        logger.info(f"连接池已启动: min_size={self.min_size}, max_size={self.max_size}")
        
    async def stop(self):
        """停止连接池"""
        if self._maintenance_task:
            self._maintenance_task.cancel()
            
        async with self._lock:
            for conn_id, info in list(self._pool.items()):
                await self._close_connection(conn_id)
        logger.info("连接池已停止")
        
    async def get_connection(self) -> ClientConnection:
        """获取一个可用连接"""
        async with self._lock:
            # 查找空闲连接
            for conn_id, info in self._pool.items():
                if not info.is_busy:
                    info.is_busy = True
                    info.last_used = datetime.now()
                    return info.connection
                    
            # 如果没有空闲连接且未达到最大连接数，创建新连接
            if len(self._pool) < self.max_size:
                conn_id = await self._create_connection()
                info = self._pool[conn_id]
                info.is_busy = True
                return info.connection
                
            # 等待空闲连接
            while True:
                for conn_id, info in self._pool.items():
                    if not info.is_busy:
                        info.is_busy = True
                        info.last_used = datetime.now()
                        return info.connection
                await asyncio.sleep(0.1)
                
    async def release_connection(self, connection: ClientConnection):
        """释放连接"""
        async with self._lock:
            for conn_id, info in self._pool.items():
                if info.connection == connection:
                    info.is_busy = False
                    info.last_used = datetime.now()
                    break
                    
    async def _create_connection(self) -> str:
        """创建新连接"""
        for _ in range(self.retry_limit):
            try:
                connection = await connect(
                    f"ws://{self.host}:{self.port}",
                    ping_interval=20,
                    ping_timeout=10
                )
                conn_id = str(id(connection))
                self._pool[conn_id] = ConnectionInfo(
                    connection=connection,
                    created_at=datetime.now(),
                    last_used=datetime.now()
                )
                logger.debug(f"创建新连接: {conn_id}")
                return conn_id
            except Exception as e:
                logger.error(f"创建连接失败: {e}")
                await asyncio.sleep(1)
        raise ConnectionError("无法创建新连接")
        
    async def _close_connection(self, conn_id: str):
        """关闭连接"""
        if conn_id in self._pool:
            info = self._pool[conn_id]
            try:
                await info.connection.close()
            except Exception as e:
                logger.error(f"关闭连接失败: {e}")
            del self._pool[conn_id]
            
    async def _maintain_pool(self):
        """维护连接池"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                async with self._lock:
                    now = datetime.now()
                    
                    # 关闭过期连接
                    expired = []
                    for conn_id, info in list(self._pool.items()):
                        if (
                            now - info.created_at > self.max_lifetime or
                            (not info.is_busy and now - info.last_used > self.max_idle_time)
                        ):
                            expired.append(conn_id)
                            
                    for conn_id in expired:
                        await self._close_connection(conn_id)
                        
                    # 确保最小连接数
                    while len(self._pool) < self.min_size:
                        await self._create_connection()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"连接池维护失败: {e}")
                
    def get_stats(self) -> Dict[str, int]:
        """获取连接池统计信息"""
        total = len(self._pool)
        busy = sum(1 for info in self._pool.values() if info.is_busy)
        return {
            "total_connections": total,
            "busy_connections": busy,
            "idle_connections": total - busy
        } 