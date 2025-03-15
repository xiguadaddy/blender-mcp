"""BlenderMCP批量操作测试模块"""

import pytest
import asyncio
from datetime import datetime, timedelta
from blendermcp.client.batch import BatchManager, BatchOperation, BatchResult

@pytest.fixture
async def batch_manager():
    """创建测试批量操作管理器"""
    manager = BatchManager(
        max_batch_size=5,
        flush_interval=0.1,
        compression_threshold=100
    )
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_batch_initialization(batch_manager):
    """测试批量操作管理器初始化"""
    assert batch_manager.max_batch_size == 5
    assert batch_manager.flush_interval == 0.1
    assert batch_manager.compression_threshold == 100
    assert len(batch_manager._operations) == 0

@pytest.mark.asyncio
async def test_add_operation(batch_manager):
    """测试添加操作"""
    # 添加单个操作
    op_id = await batch_manager.add_operation(
        command="create_object",
        params={"type": "MESH", "name": "Cube"}
    )
    assert op_id.startswith("op_")
    assert len(batch_manager._operations) == 1
    
    # 验证操作内容
    operation = batch_manager._operations[op_id]
    assert operation.command == "create_object"
    assert operation.params == {"type": "MESH", "name": "Cube"}
    assert isinstance(operation.created_at, datetime)
    assert operation.priority == 0
    assert operation.depends_on == []

@pytest.mark.asyncio
async def test_batch_size_limit(batch_manager):
    """测试批处理大小限制"""
    # 添加超过最大批处理大小的操作
    operations = []
    for i in range(batch_manager.max_batch_size + 1):
        op_id = await batch_manager.add_operation(
            command="create_object",
            params={"name": f"Object_{i}"}
        )
        operations.append(op_id)
        
    # 验证自动刷新
    assert len(batch_manager._operations) < batch_manager.max_batch_size

@pytest.mark.asyncio
async def test_operation_priority(batch_manager):
    """测试操作优先级"""
    # 添加不同优先级的操作
    op1 = await batch_manager.add_operation(
        command="cmd1",
        params={},
        priority=1
    )
    op2 = await batch_manager.add_operation(
        command="cmd2",
        params={},
        priority=2
    )
    op3 = await batch_manager.add_operation(
        command="cmd3",
        params={},
        priority=0
    )
    
    # 刷新并验证顺序
    sorted_ops = batch_manager._sort_operations()
    sorted_ids = [op_id for op_id, _ in sorted_ops]
    
    assert sorted_ids.index(op2) < sorted_ids.index(op1)
    assert sorted_ids.index(op1) < sorted_ids.index(op3)

@pytest.mark.asyncio
async def test_operation_dependencies(batch_manager):
    """测试操作依赖关系"""
    # 创建带依赖的操作
    op1 = await batch_manager.add_operation(
        command="cmd1",
        params={}
    )
    op2 = await batch_manager.add_operation(
        command="cmd2",
        params={},
        depends_on=[op1]
    )
    op3 = await batch_manager.add_operation(
        command="cmd3",
        params={},
        depends_on=[op2]
    )
    
    # 验证依赖顺序
    sorted_ops = batch_manager._sort_operations()
    sorted_ids = [op_id for op_id, _ in sorted_ops]
    
    assert sorted_ids.index(op1) < sorted_ids.index(op2)
    assert sorted_ids.index(op2) < sorted_ids.index(op3)

@pytest.mark.asyncio
async def test_auto_flush(batch_manager):
    """测试自动刷新"""
    # 添加一些操作
    await batch_manager.add_operation(
        command="cmd1",
        params={}
    )
    await batch_manager.add_operation(
        command="cmd2",
        params={}
    )
    
    # 等待自动刷新，设置较短的超时时间
    try:
        async with asyncio.timeout(0.5):  # 设置0.5秒超时
            await asyncio.sleep(batch_manager.flush_interval * 1.5)
            
            # 验证操作已被清空
            assert len(batch_manager._operations) == 0
    except asyncio.TimeoutError:
        pytest.fail("自动刷新测试超时")

@pytest.mark.asyncio
async def test_manual_flush(batch_manager):
    """测试手动刷新"""
    # 添加操作
    await batch_manager.add_operation(
        command="cmd1",
        params={"param1": "value1"}
    )
    await batch_manager.add_operation(
        command="cmd2",
        params={"param2": "value2"}
    )
    
    # 手动刷新
    results = await batch_manager.flush()
    
    # 验证结果
    assert len(results) == 2
    assert results[0]["command"] == "cmd1"
    assert results[1]["command"] == "cmd2"
    assert len(batch_manager._operations) == 0

@pytest.mark.asyncio
async def test_batch_result():
    """测试批量操作结果"""
    # 创建成功结果
    success_result = BatchResult(
        operation_id="op_1",
        success=True,
        result={"data": "success"}
    )
    assert success_result.success
    assert success_result.result["data"] == "success"
    assert success_result.error is None
    
    # 创建失败结果
    error_result = BatchResult(
        operation_id="op_2",
        success=False,
        error="Operation failed"
    )
    assert not error_result.success
    assert error_result.result is None
    assert error_result.error == "Operation failed"
    
    # 测试转换为字典
    result_dict = success_result.to_dict()
    assert result_dict["operation_id"] == "op_1"
    assert result_dict["success"]
    assert "timestamp" in result_dict

@pytest.mark.asyncio
async def test_get_stats(batch_manager):
    """测试获取统计信息"""
    # 添加一些操作
    await batch_manager.add_operation(
        command="cmd1",
        params={}
    )
    await batch_manager.add_operation(
        command="cmd2",
        params={}
    )
    
    # 获取统计信息
    stats = batch_manager.get_stats()
    assert stats["pending_operations"] == 2
    assert stats["operation_counter"] == 2 