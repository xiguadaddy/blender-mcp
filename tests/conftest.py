"""
BlenderMCP 测试配置
"""

import sys
import os
import pytest
import asyncio
import aiohttp
from unittest.mock import MagicMock
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 服务器配置
SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
SERVER_PORT = int(os.getenv('SERVER_PORT', '9876'))
SERVER_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

# 模拟bpy模块
class MockBlenderObject:
    def __init__(self):
        self.location = [0, 0, 0]
        self.rotation_euler = [0, 0, 0]
        self.scale = [1, 1, 1]
        self.type = 'MESH'
        self.name = 'test_object'
        self.data = MagicMock()
        self.visible_get = MagicMock(return_value=True)
        self.visible_set = MagicMock()

class MockBlenderContext:
    def __init__(self):
        self.scene = MagicMock()
        self.scene.objects = []
        self.scene.camera = None

class MockBlenderData:
    def __init__(self):
        self.objects = []
        self.materials = []
        self.lights = []
        self.cameras = []

class MockBpy:
    def __init__(self):
        self.context = MockBlenderContext()
        self.data = MockBlenderData()
        self.ops = MagicMock()
        self.types = MagicMock()

@pytest.fixture(autouse=True)
def mock_bpy(monkeypatch):
    """自动模拟bpy模块"""
    mock_bpy = MockBpy()
    monkeypatch.setattr('sys.modules', {'bpy': mock_bpy, **sys.modules})
    return mock_bpy

@pytest.fixture
async def server_session():
    """创建服务器会话"""
    async with aiohttp.ClientSession() as session:
        yield session

@pytest.fixture
async def server_connection(server_session):
    """创建服务器WebSocket连接"""
    async with server_session.ws_connect(SERVER_URL) as ws:
        yield ws

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 