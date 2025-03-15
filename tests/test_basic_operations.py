"""
Basic operations test for BlenderMCP
"""

import asyncio
import logging
import json
from blendermcp.client.client import BlenderMCPClient

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connection(client: BlenderMCPClient) -> bool:
    """测试服务器连接"""
    try:
        await client.connect()
        scene_info = await client.get_scene_info()
        logger.info(f"Scene info: {json.dumps(scene_info, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

async def test_object_creation(client: BlenderMCPClient) -> bool:
    """测试对象创建"""
    try:
        # 创建一个白色立方体
        white_cube = await client.create_object(
            type="CUBE",
            name="white_cube",
            location=[1, 0, 0]
        )
        logger.info(f"Created white cube: {white_cube}")
        
        # 创建一个黑色立方体
        black_cube = await client.create_object(
            type="CUBE",
            name="black_cube",
            location=[-1, 0, 0]
        )
        logger.info(f"Created black cube: {black_cube}")
        
        return True
    except Exception as e:
        logger.error(f"Object creation test failed: {e}")
        return False

async def test_material_application(client: BlenderMCPClient) -> bool:
    """测试材质应用"""
    try:
        # 为白色立方体设置材质
        await client.set_material(
            object_name="white_cube",
            material_name="white_material",
            color=[1, 1, 1]
        )
        
        # 为黑色立方体设置材质
        await client.set_material(
            object_name="black_cube",
            material_name="black_material",
            color=[0, 0, 0]
        )
        
        return True
    except Exception as e:
        logger.error(f"Material application test failed: {e}")
        return False

async def test_scene_query(client: BlenderMCPClient) -> bool:
    """测试场景查询"""
    try:
        # 获取白色立方体信息
        white_cube_info = await client.get_object_info("white_cube")
        logger.info(f"White cube info: {json.dumps(white_cube_info, indent=2)}")
        
        # 获取黑色立方体信息
        black_cube_info = await client.get_object_info("black_cube")
        logger.info(f"Black cube info: {json.dumps(black_cube_info, indent=2)}")
        
        return True
    except Exception as e:
        logger.error(f"Scene query test failed: {e}")
        return False

async def cleanup_scene(client: BlenderMCPClient) -> bool:
    """清理测试场景"""
    try:
        # 删除测试对象
        await client.delete_object("white_cube")
        await client.delete_object("black_cube")
        return True
    except Exception as e:
        logger.error(f"Scene cleanup failed: {e}")
        return False

async def run_tests():
    """运行所有测试"""
    client = BlenderMCPClient()
    
    try:
        # 运行测试
        if not await test_connection(client):
            logger.error("Connection test failed")
            return
            
        if not await test_object_creation(client):
            logger.error("Object creation test failed")
            return
            
        if not await test_material_application(client):
            logger.error("Material application test failed")
            return
            
        if not await test_scene_query(client):
            logger.error("Scene query test failed")
            return
            
        # 清理场景
        await cleanup_scene(client)
        
        logger.info("All tests completed successfully")
        
    except Exception as e:
        logger.error(f"Tests failed: {e}")
        
    finally:
        # 断开连接
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_tests()) 