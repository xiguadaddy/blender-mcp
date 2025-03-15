"""
Basic operations test for BlenderMCP
"""

import asyncio
import logging
import json
import time
from blendermcp.client.client import BlenderMCPClient
import pytest
from unittest.mock import Mock, patch
from asyncio import TimeoutError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义测试超时时间（秒）
TEST_TIMEOUT = 10
OPERATION_TIMEOUT = 5

@pytest.fixture
async def client():
    """创建测试客户端"""
    client = BlenderMCPClient()
    try:
        await asyncio.wait_for(client.start(), timeout=TEST_TIMEOUT)
        yield client
    except TimeoutError:
        logger.error("客户端启动超时")
        raise
    except Exception as e:
        logger.error(f"客户端启动失败: {e}")
        raise
    finally:
        try:
            await asyncio.wait_for(client.stop(), timeout=OPERATION_TIMEOUT)
        except Exception as e:
            logger.error(f"客户端停止失败: {e}")

async def wait_for_server(client: BlenderMCPClient, max_attempts: int = 3, delay: float = 1.0) -> bool:
    """等待服务器启动"""
    for attempt in range(max_attempts):
        try:
            logger.info(f"尝试连接服务器 (尝试 {attempt + 1}/{max_attempts})")
            await asyncio.wait_for(client.connect(), timeout=OPERATION_TIMEOUT)
            logger.info("成功连接到服务器")
            return True
        except TimeoutError:
            logger.warning(f"连接超时，尝试 {attempt + 1}/{max_attempts}")
        except Exception as e:
            logger.warning(f"连接失败: {e}，尝试 {attempt + 1}/{max_attempts}")
        
        if attempt < max_attempts - 1:
            await asyncio.sleep(delay)
    
    logger.error("无法连接到服务器")
    return False

@pytest.mark.asyncio
async def test_connection(client):
    """测试服务器连接"""
    try:
        # 获取场景信息
        scene_info = await asyncio.wait_for(
            client.get_scene_info(),
            timeout=OPERATION_TIMEOUT
        )
        assert "result" in scene_info
        assert "objects" in scene_info["result"]
        logger.info(f"场景信息: {json.dumps(scene_info, indent=2)}")
    except TimeoutError:
        pytest.fail("获取场景信息超时")
    except Exception as e:
        pytest.fail(f"获取场景信息失败: {e}")

@pytest.mark.asyncio
async def test_object_creation(client):
    """测试对象创建"""
    try:
        # 创建测试对象
        result = await asyncio.wait_for(
            client.create_object(
                object_type="MESH",
                object_name="test_cube",
                location=[0, 0, 0]
            ),
            timeout=OPERATION_TIMEOUT
        )
        
        assert "result" in result
        assert "object_name" in result["result"]
        assert "location" in result["result"]
        logger.info(f"创建对象结果: {json.dumps(result, indent=2)}")
    except TimeoutError:
        pytest.fail("创建对象超时")
    except Exception as e:
        pytest.fail(f"创建对象失败: {e}")

@pytest.mark.asyncio
async def test_scene_query(client):
    """测试场景查询"""
    try:
        # 先创建测试对象
        create_result = await asyncio.wait_for(
            client.create_object(
                object_type="MESH",
                object_name="test_cube",
                location=[0, 0, 0]
            ),
            timeout=OPERATION_TIMEOUT
        )
        
        # 获取创建的对象名称
        assert "result" in create_result and "object_name" in create_result["result"]
        object_name = create_result["result"]["object_name"]
        logger.info(f"创建的对象名称: {object_name}")

        # 等待对象创建完成
        await asyncio.sleep(1)

        # 获取对象信息
        result = await asyncio.wait_for(
            client.get_object_info(object_name),
            timeout=OPERATION_TIMEOUT
        )
        
        assert not result.get("error")
        assert "result" in result
        logger.info(f"对象信息: {json.dumps(result, indent=2)}")
    except TimeoutError:
        pytest.fail("查询场景超时")
    except Exception as e:
        pytest.fail(f"查询场景失败: {e}")

@pytest.mark.asyncio
async def test_material_application(client):
    """测试材质应用"""
    try:
        # 先创建测试对象
        await asyncio.wait_for(
            client.create_object(
                object_type="MESH",
                object_name="test_cube",
                location=[0, 0, 0]
            ),
            timeout=OPERATION_TIMEOUT
        )
        
        # 等待对象创建完成
        await asyncio.sleep(1)

        # 设置材质
        result = await asyncio.wait_for(
            client.set_material(
                object_name="test_cube",
                material_name="test_material",
                color=[1, 0, 0, 1]
            ),
            timeout=OPERATION_TIMEOUT
        )
        
        assert "content" in result
        assert len(result["content"]) > 0
        assert "text" in result["content"][0]
        logger.info(f"设置材质结果: {json.dumps(result, indent=2)}")
    except TimeoutError:
        pytest.fail("设置材质超时")
    except Exception as e:
        pytest.fail(f"设置材质失败: {e}")

@pytest.mark.asyncio
async def test_cleanup(client):
    """测试清理场景"""
    try:
        # 先创建测试对象
        create_result = await asyncio.wait_for(
            client.create_object(
                object_type="MESH",
                object_name="test_cube",
                location=[0, 0, 0]
            ),
            timeout=OPERATION_TIMEOUT
        )
        
        # 获取创建的对象名称
        assert "result" in create_result and "object_name" in create_result["result"]
        object_name = create_result["result"]["object_name"]
        logger.info(f"创建的对象名称: {object_name}")

        # 等待对象创建完成
        await asyncio.sleep(1)

        # 删除测试对象
        result = await asyncio.wait_for(
            client.delete_object(object_name),
            timeout=OPERATION_TIMEOUT
        )
        
        assert not result.get("error")
        logger.info(f"删除对象结果: {json.dumps(result, indent=2)}")

        # 验证对象已被删除
        scene_info = await asyncio.wait_for(
            client.get_scene_info(),
            timeout=OPERATION_TIMEOUT
        )
        objects = scene_info["result"]["objects"]
        assert object_name not in [obj["object_name"] for obj in objects]
    except TimeoutError:
        pytest.fail("清理场景超时")
    except Exception as e:
        pytest.fail(f"清理场景失败: {e}")

async def cleanup_scene(client: BlenderMCPClient) -> bool:
    """清理测试场景"""
    try:
        # 删除测试对象
        await asyncio.wait_for(
            client.delete_object("test_cube"),
            timeout=OPERATION_TIMEOUT
        )
        return True
    except TimeoutError:
        logger.error("清理场景超时")
        return False
    except Exception as e:
        logger.error(f"清理场景失败: {e}")
        return False

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 