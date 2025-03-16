#!/usr/bin/env python3
"""
BlenderMCP 示例脚本 - 创建国际象棋棋盘和棋子
演示如何使用BlenderMCP API创建一个完整的场景
"""

import sys
import os
import json
import socket
import time
import traceback  # 添加traceback模块用于详细错误信息
import random
import asyncio
import logging
from blendermcp.client import BlenderMCPClient

# 确保可以导入客户端类
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blendermcp.client import BlenderMCPClient

# 设置调试级别
DEBUG = True  # 可以控制是否输出详细日志

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_print(message):
    """调试信息输出函数"""
    if DEBUG:
        print(f"[DEBUG] {message}")

def check_response(response, operation_name):
    """检查响应状态，如有错误则打印"""
    if not response:
        print(f"警告: {operation_name} - 响应为空")
        return False
    
    if "error" in response:
        print(f"错误: {operation_name} - {response['error']}")
        return False
    
    if "status" in response and response["status"] == "error":
        print(f"错误: {operation_name} - {response.get('message', '未知错误')}")
        return False
    
    debug_print(f"{operation_name} - 成功")
    return True

def get_object_name(response):
    """从响应中获取对象名称，处理不同的响应格式"""
    if response is None:
        debug_print("警告: 响应为None")
        return None
        
    debug_print(f"响应类型: {type(response)}, 内容: {json.dumps(response, ensure_ascii=False)[:100]}")
    
    if isinstance(response, dict):
        if "status" in response and response["status"] == "error":
            debug_print(f"错误响应: {response.get('message', '未知错误')}")
            return None
            
        if "result" in response and isinstance(response["result"], dict):
            if "object_name" in response["result"]:
                return response["result"]["object_name"]
            if "name" in response["result"]:
                return response["result"]["name"]
            if "object" in response["result"]:
                return response["result"]["object"]
                
        if "name" in response:
            return response["name"]
    
    debug_print(f"无法从响应中提取对象名称: {json.dumps(response, ensure_ascii=False)[:100]}")
    return None

async def create_chess_board(client: BlenderMCPClient):
    """创建棋盘"""
    # 创建棋盘底座
    board_base = await client.create_object(
        object_type="MESH",
        object_name="chess_board",
        location=[0, 0, -0.1], 
        scale=[4, 4, 0.2]
    )
    board_name = get_object_name(board_base)
    logger.info(f"创建棋盘底座: {board_base}")
    
    # 为棋盘底座设置木质材质
    await client.set_material(
        object_name=board_name,
        material_name="board_wood",
        color=[0.4, 0.2, 0.1, 1.0]  # 使用列表而不是元组
    )
    
    # 创建64个棋盘格
    for i in range(8):
        for j in range(8):
            # 计算位置
            x = (i - 3.5) * 0.5
            y = (j - 3.5) * 0.5
            # 确定颜色
            is_white = (i + j) % 2 == 0
            color = [0.9, 0.9, 0.9, 1.0] if is_white else [0.1, 0.1, 0.1, 1.0]  # 使用列表
            
            # 创建格子
            square = await client.create_object(
                object_type="MESH",
                object_name=f"square_{i}_{j}",
                location=[x, y, 0],
                scale=[0.25, 0.25, 0.01]
            )
            square_name = get_object_name(square)
            logger.info(f"创建棋盘格 {i},{j}: {square}")
            
            # 设置材质
            material_name = f"{'white' if is_white else 'black'}_square"
            await client.set_material(
                object_name=square_name,
                material_name=material_name,
                color=color
            )

async def create_chess_piece(client: BlenderMCPClient, piece_type: str, is_white: bool, position: tuple):
    """创建棋子
    
    Args:
        client: BlenderMCP客户端
        piece_type: 棋子类型 (pawn, rook, knight, bishop, queen, king)
        is_white: 是否为白方棋子
        position: 棋盘位置 (x, y)
    """
    # 计算实际位置
    x = (position[0] - 3.5) * 0.5
    y = (position[1] - 3.5) * 0.5
    color = [0.9, 0.9, 0.9, 1.0] if is_white else [0.1, 0.1, 0.1, 1.0]  # 使用列表
    side = "white" if is_white else "black"
    
    # 根据棋子类型设置不同的形状和大小
    piece_params = {
        "pawn": {"object_type": "MESH", "height": 0.3, "scale": [0.1, 0.1, 0.3]},
        "rook": {"object_type": "MESH", "height": 0.4, "scale": [0.15, 0.15, 0.4]},
        "knight": {"object_type": "MESH", "height": 0.4, "scale": [0.12, 0.12, 0.4]},
        "bishop": {"object_type": "MESH", "height": 0.5, "scale": [0.12, 0.12, 0.5]},
        "queen": {"object_type": "MESH", "height": 0.6, "scale": [0.15, 0.15, 0.6]},
        "king": {"object_type": "MESH", "height": 0.7, "scale": [0.15, 0.15, 0.7]}
    }
    
    params = piece_params[piece_type]
    piece = await client.create_object(
        object_type=params["object_type"],
        object_name=f"{side}_{piece_type}_{position[0]}_{position[1]}",
        location=[x, y, params["height"]],
        scale=params["scale"]
    )
    piece_name = get_object_name(piece)
    logger.info(f"创建{side} {piece_type}: {piece}")
    
    # 设置材质，只使用基本参数
    material_name = f"{side}_{piece_type}_material"
    await client.set_material(
        object_name=piece_name,
        material_name=material_name,
        color=color
    )

async def create_chess_set():
    """创建完整的国际象棋套装"""
    try:
        # 连接到Blender
        client = BlenderMCPClient()
        await client.start()
        logger.info("已连接到Blender")
        
        # 清除现有场景中的对象（可选）
        scene_info = await client.get_scene_info()
        if scene_info.get("objects"):
            for obj in scene_info["objects"]:
                if obj["name"] != "Camera":  # 保留相机
                    await client.delete_object(obj["name"])
        
        # 创建棋盘
        await create_chess_board(client)
        
        # 创建白方棋子
        # 白方兵
        for i in range(8):
            await create_chess_piece(client, "pawn", True, (i, 1))
        # 白方其他棋子
        piece_types = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"]
        for i, piece_type in enumerate(piece_types):
            await create_chess_piece(client, piece_type, True, (i, 0))
            
        # 创建黑方棋子
        # 黑方兵
        for i in range(8):
            await create_chess_piece(client, "pawn", False, (i, 6))
        # 黑方其他棋子
        for i, piece_type in enumerate(piece_types):
            await create_chess_piece(client, piece_type, False, (i, 7))
            
        # 设置相机和灯光
        # 添加日光
        await client.create_object(
            object_type="LIGHT",
            object_name="Sun",
            location=[5, 5, 10],
            rotation=[0.9, 0, 0.8]
        )
        await client._send_command("set_light_type", {"object_name": "Sun", "light_type": "SUN"})
        await client._send_command("set_light_energy", {"object_name": "Sun", "energy": 3.0})
        
        # 添加区域光源
        await client._send_command("advanced_lighting", {
            "object_name": "Chess_Light",
            "light_type": "AREA",
            "location": [0, 0, 5],
            "energy": 50,
            "color": [1.0, 0.95, 0.9]
        })
        
        # 设置相机
        camera = await client.create_object(
            object_type="CAMERA",
            object_name="ChessCamera",
            location=[8, -6, 6],
            rotation=[0.9, 0, 0.8]
        )
        await client._send_command("set_active_camera", {"object_name": camera["result"]["object_name"]})
        
        logger.info("国际象棋套装创建完成")

except Exception as e:
            logger.error(f"创建国际象棋套装时出错: {e}")
            logger.error(traceback.format_exc())
finally:
            await client.stop()
            logger.info("已断开与Blender的连接")

if __name__ == "__main__":
    asyncio.run(create_chess_set())
