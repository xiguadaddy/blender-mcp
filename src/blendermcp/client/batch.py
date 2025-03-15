"""BlenderMCP批量操作管理模块"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class BatchOperation:
    """批量操作定义"""
    command: str
    params: Dict[str, Any]
    created_at: datetime
    priority: int = 0
    depends_on: List[str] = None

class BatchManager:
    """批量操作管理器"""
    
    def __init__(
        self,
        max_batch_size: int = 100,
        flush_interval: float = 1.0,
        compression_threshold: int = 1024
    ):
        """初始化批量操作管理器
        
        Args:
            max_batch_size: 最大批处理大小
            flush_interval: 自动刷新间隔(秒)
            compression_threshold: 压缩阈值(字节)
        """
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self.compression_threshold = compression_threshold
        
        self._operations: Dict[str, BatchOperation] = {}
        self._lock = asyncio.Lock()
        self._flush_task = None
        self._operation_counter = 0
        self._running = False
        
    async def start(self):
        """启动批量操作管理器"""
        self._running = True
        self._flush_task = asyncio.create_task(self._auto_flush())
        logger.info(f"批量操作管理器已启动: max_size={self.max_batch_size}")
        
    async def stop(self):
        """停止批量操作管理器"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        logger.info("批量操作管理器已停止")
        
    async def add_operation(
        self,
        command: str,
        params: Dict[str, Any],
        priority: int = 0,
        depends_on: List[str] = None
    ) -> str:
        """添加批量操作
        
        Args:
            command: 命令名称
            params: 命令参数
            priority: 优先级(0-9)
            depends_on: 依赖的操作ID列表
            
        Returns:
            操作ID
        """
        async with self._lock:
            operation_id = f"op_{self._operation_counter}"
            self._operation_counter += 1
            
            self._operations[operation_id] = BatchOperation(
                command=command,
                params=params,
                created_at=datetime.now(),
                priority=priority,
                depends_on=depends_on or []
            )
            
            # 如果达到最大批处理大小，自动刷新
            if len(self._operations) >= self.max_batch_size:
                await self.flush()
                
            return operation_id
            
    async def flush(self) -> List[Dict[str, Any]]:
        """刷新所有待处理的操作
        
        Returns:
            已处理的操作结果列表
        """
        async with self._lock:
            if not self._operations:
                return []
                
            # 按优先级和依赖关系排序操作
            sorted_ops = self._sort_operations()
            
            # 构建批处理消息
            batch_message = {
                "type": "batch",
                "operations": [
                    {
                        "id": op_id,
                        "command": op.command,
                        "params": op.params
                    }
                    for op_id, op in sorted_ops
                ]
            }
            
            # 检查是否需要压缩
            message_size = len(json.dumps(batch_message))
            if message_size > self.compression_threshold:
                batch_message["compressed"] = True
                # 这里可以添加压缩逻辑
                
            # 清空操作列表
            self._operations.clear()
            
            return batch_message["operations"]
            
    def _sort_operations(self) -> List[tuple[str, BatchOperation]]:
        """按优先级和依赖关系排序操作"""
        # 构建依赖图
        graph = {op_id: set(op.depends_on) for op_id, op in self._operations.items()}
        
        # 拓扑排序
        sorted_ops = []
        visited = set()
        temp_visited = set()
        
        def visit(op_id: str):
            if op_id in temp_visited:
                raise ValueError(f"检测到循环依赖: {op_id}")
            if op_id in visited:
                return
                
            temp_visited.add(op_id)
            
            # 先处理依赖
            for dep_id in graph[op_id]:
                visit(dep_id)
                
            temp_visited.remove(op_id)
            visited.add(op_id)
            sorted_ops.append((op_id, self._operations[op_id]))
            
        # 按优先级从高到低遍历操作
        for op_id, op in sorted(
            self._operations.items(),
            key=lambda x: (-x[1].priority, x[1].created_at)
        ):
            if op_id not in visited:
                visit(op_id)
                
        return sorted_ops
        
    async def _auto_flush(self):
        """自动刷新任务"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                if self._running:  # 再次检查，避免在sleep期间被停止
                    await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动刷新失败: {e}")
                if not self._running:  # 如果已停止，退出循环
                    break
                
    def get_stats(self) -> Dict[str, Any]:
        """获取批量操作统计信息"""
        return {
            "pending_operations": len(self._operations),
            "operation_counter": self._operation_counter
        }
        
class BatchResult:
    """批量操作结果"""
    
    def __init__(self, operation_id: str, success: bool, result: Any = None, error: str = None):
        self.operation_id = operation_id
        self.success = success
        self.result = result
        self.error = error
        self.timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "operation_id": self.operation_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }