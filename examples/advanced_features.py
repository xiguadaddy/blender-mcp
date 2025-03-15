#!/usr/bin/env python3
"""
BlenderMCP高级功能示例脚本
演示如何使用新的MCP客户端系统的高级功能
"""

import asyncio
import logging
from pathlib import Path
from blendermcp.client import BlenderMCPClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demonstrate_advanced_features():
    """演示高级功能的使用"""
    try:
        # 创建客户端实例，使用自定义配置文件
        config_path = Path(__file__).parent / "mcp.json"
        client = BlenderMCPClient(str(config_path))
        
        # 连接到服务器
        await client.connect()
        logger.info("已连接到Blender服务器")
        
        # 列出所有可用工具
        logger.info("可用工具类别:")
        categories = client.get_tool_categories()
        for category in categories:
            logger.info(f"\n{category.upper()}类工具:")
            tools = client.list_available_tools(category)
            for tool in tools:
                logger.info(f"- {tool['name']}: {tool['description']}")
                
        # 创建一个使用节点材质的金属球体
        sphere = await client.create_object(
            type="SPHERE",
            name="metal_sphere",
            location=[0, 0, 0],
            scale=[1, 1, 1]
        )
        
        # 使用预设的金属材质
        await client.create_node_material(
            name="metal_material",
            node_setup={
                "nodes": {
                    "principled": {
                        "type": "ShaderNodeBsdfPrincipled",
                        "location": [0, 0],
                        "properties": {
                            "metallic": 1.0,
                            "roughness": 0.2,
                            "base_color": [0.8, 0.8, 0.8, 1.0]
                        }
                    },
                    "output": {
                        "type": "ShaderNodeOutputMaterial",
                        "location": [300, 0]
                    }
                },
                "links": [
                    {
                        "from_node": "principled",
                        "from_socket": "BSDF",
                        "to_node": "output",
                        "to_socket": "Surface"
                    }
                ]
            }
        )
        
        # 创建三点灯光布局
        # 主光源
        await client.create_light(
            type="AREA",
            name="key_light",
            location=[5, -5, 5],
            energy=1000,
            color=[1.0, 0.95, 0.8]
        )
        
        # 补光
        await client.create_light(
            type="AREA",
            name="fill_light",
            location=[-5, -2, 3],
            energy=400,
            color=[0.8, 0.87, 1.0]
        )
        
        # 背光
        await client.create_light(
            type="AREA",
            name="back_light",
            location=[0, 5, 3],
            energy=600,
            color=[1.0, 1.0, 1.0]
        )
        
        # 添加一个细分曲面修改器
        await client.add_modifier(
            object_name="metal_sphere",
            modifier_type="SUBSURF",
            parameters={
                "levels": 2,
                "render_levels": 3
            }
        )
        
        # 设置渲染参数
        await client.set_render_settings(
            engine="CYCLES",
            samples=128,
            resolution_x=1920,
            resolution_y=1080,
            use_gpu=True
        )
        
        # 创建一个简单的旋转动画
        await client.create_animation(
            object_name="metal_sphere",
            property_path="rotation_euler",
            keyframes={
                "1": [0, 0, 0],
                "120": [0, 0, 6.28319]  # 360度
            }
        )
        
        # 渲染图像
        output_path = str(Path(__file__).parent / "render_result.png")
        await client.render_image(
            output_path=output_path,
            format="PNG",
            quality=90
        )
        
        logger.info(f"渲染完成，结果保存在: {output_path}")
        
    except Exception as e:
        logger.error(f"演示过程中出错: {e}")
    finally:
        await client.disconnect()
        logger.info("已断开与服务器的连接")

if __name__ == "__main__":
    asyncio.run(demonstrate_advanced_features()) 