"""
BlenderMCP 连接管理模块
"""

import asyncio
import websockets
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """连接信息"""
    url: str
    session_id: Optional[str] = None
    created_at: datetime = datetime.now()
    last_used: datetime = datetime.now()
    
class ConnectionPool:
    """连接池管理器"""
    
    def __init__(self, max_connections: int = 10, timeout: int = 300):
        """初始化连接池
        
        Args:
            max_connections: 最大连接数
            timeout: 连接超时时间（秒）
        """
        self.max_connections = max_connections
        self.timeout = timedelta(seconds=timeout)
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.connection_info: Dict[str, ConnectionInfo] = {}
        self._cleanup_task = None
        
    async def get_connection(self, url: str) -> websockets.WebSocketClientProtocol:
        """获取连接
        
        Args:
            url: WebSocket服务器URL
            
        Returns:
            WebSocket连接
        """
        # 清理过期连接
        await self._cleanup_expired()
        
        # 检查现有连接
        for conn_id, conn in self.connections.items():
            info = self.connection_info[conn_id]
            if info.url == url and not conn.closed:
                info.last_used = datetime.now()
                return conn
                
        # 创建新连接
        if len(self.connections) >= self.max_connections:
            # 移除最旧的连接
            oldest_conn_id = min(
                self.connection_info.items(),
                key=lambda x: x[1].last_used
            )[0]
            await self.close_connection(oldest_conn_id)
            
        conn = await websockets.connect(url)
        conn_id = str(id(conn))
        self.connections[conn_id] = conn
        self.connection_info[conn_id] = ConnectionInfo(url=url)
        
        return conn
        
    async def close_connection(self, conn_id: str):
        """关闭连接
        
        Args:
            conn_id: 连接ID
        """
        if conn_id in self.connections:
            conn = self.connections[conn_id]
            if not conn.closed:
                await conn.close()
            del self.connections[conn_id]
            del self.connection_info[conn_id]
            
    async def _cleanup_expired(self):
        """清理过期连接"""
        now = datetime.now()
        expired_conns = [
            conn_id
            for conn_id, info in self.connection_info.items()
            if now - info.last_used > self.timeout
        ]
        for conn_id in expired_conns:
            await self.close_connection(conn_id)
            
    async def close_all(self):
        """关闭所有连接"""
        for conn_id in list(self.connections.keys()):
            await self.close_connection(conn_id)
            
    def start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            await self._cleanup_expired()
            await asyncio.sleep(60)  # 每分钟清理一次
            
    def stop_cleanup_task(self):
        """停止清理任务"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            
    def get_stats(self) -> Dict[str, int]:
        """获取连接池统计信息"""
        total = len(self.connections)
        return {
            "total_connections": total,
            "idle_connections": total
        } 