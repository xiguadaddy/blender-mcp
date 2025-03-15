"""BlenderMCP客户端测试模块"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch
from blendermcp.client.client import BlenderMCPClient
from blendermcp.client.errors import ValidationError, ConnectionError
from blendermcp.client.api_spec import API_VERSION, APICategory

@pytest.fixture
async def client():
    """创建测试客户端"""
    client = BlenderMCPClient()
    return client

@pytest.mark.asyncio
async def test_client_initialization(client):
    """测试客户端初始化"""
    assert client.host == "localhost"
    assert client.port == 9876
    assert client.websocket is None
    assert client.api_version == API_VERSION
    assert len(client.tool_registry.tools) > 0

@pytest.mark.asyncio
async def test_validate_request(client):
    """测试API请求验证"""
    # 测试有效请求
    params = {
        "object_type": "MESH",
        "object_name": "Cube",
        "location": [0, 0, 0]
    }
    assert await client._validate_request("create_object", params) is True
    
    # 测试无效端点
    with pytest.raises(ValidationError):
        await client._validate_request("invalid_endpoint", {})
        
    # 测试无效参数
    invalid_params = {
        "object_type": 123,  # 应该是字符串
        "location": "invalid"  # 应该是数组
    }
    with pytest.raises(ValidationError):
        await client._validate_request("create_object", invalid_params)

@pytest.mark.asyncio
async def test_create_object(client):
    """测试创建对象API"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_ws.send = Mock()
        mock_ws.recv = Mock(return_value=json.dumps({"success": True}))
        mock_connect.return_value = mock_ws
        
        response = await client.create_object(
            object_type="MESH",
            object_name="TestCube",
            location=[1, 2, 3]
        )
        
        assert response["content"][0]["type"] == "text"
        assert "对象创建成功" in response["content"][0]["text"]
        
        # 验证发送的命令
        sent_command = json.loads(mock_ws.send.call_args[0][0])
        assert sent_command["command"] == "create_object"
        assert sent_command["version"] == API_VERSION
        assert sent_command["params"]["object_type"] == "MESH"
        assert sent_command["params"]["object_name"] == "TestCube"
        assert sent_command["params"]["location"] == [1, 2, 3]

@pytest.mark.asyncio
async def test_set_material(client):
    """测试设置材质API"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_ws.send = Mock()
        mock_ws.recv = Mock(return_value=json.dumps({"success": True}))
        mock_connect.return_value = mock_ws
        
        response = await client.set_material(
            object_name="TestCube",
            material_name="TestMaterial",
            color=[1, 0, 0, 1]
        )
        
        assert response["content"][0]["type"] == "text"
        assert "材质设置成功" in response["content"][0]["text"]
        
        # 验证发送的命令
        sent_command = json.loads(mock_ws.send.call_args[0][0])
        assert sent_command["command"] == "set_material"
        assert sent_command["version"] == API_VERSION
        assert sent_command["params"]["object_name"] == "TestCube"
        assert sent_command["params"]["material_name"] == "TestMaterial"
        assert sent_command["params"]["color"] == [1, 0, 0, 1]

@pytest.mark.asyncio
async def test_create_light(client):
    """测试创建灯光API"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_ws.send = Mock()
        mock_ws.recv = Mock(return_value=json.dumps({"success": True}))
        mock_connect.return_value = mock_ws
        
        response = await client.create_light(
            light_type="POINT",
            object_name="TestLight",
            location=[0, 0, 5],
            energy=100,
            color=[1, 1, 1]
        )
        
        assert response["content"][0]["type"] == "text"
        assert "灯光创建成功" in response["content"][0]["text"]
        
        # 验证发送的命令
        sent_command = json.loads(mock_ws.send.call_args[0][0])
        assert sent_command["command"] == "create_light"
        assert sent_command["version"] == API_VERSION
        assert sent_command["params"]["light_type"] == "POINT"
        assert sent_command["params"]["object_name"] == "TestLight"
        assert sent_command["params"]["location"] == [0, 0, 5]
        assert sent_command["params"]["energy"] == 100
        assert sent_command["params"]["color"] == [1, 1, 1]

@pytest.mark.asyncio
async def test_render_image(client):
    """测试渲染图像API"""
    with patch("websockets.connect") as mock_connect:
        mock_ws = Mock()
        mock_ws.send = Mock()
        mock_ws.recv = Mock(return_value=json.dumps({"success": True}))
        mock_connect.return_value = mock_ws
        
        response = await client.render_image(
            output_path="render.png",
            resolution={"x": 1920, "y": 1080},
            samples=128
        )
        
        assert response["content"][0]["type"] == "text"
        assert "图像渲染成功" in response["content"][0]["text"]
        
        # 验证发送的命令
        sent_command = json.loads(mock_ws.send.call_args[0][0])
        assert sent_command["command"] == "render_image"
        assert sent_command["version"] == API_VERSION
        assert sent_command["params"]["output_path"] == "render.png"
        assert sent_command["params"]["resolution"] == {"x": 1920, "y": 1080}
        assert sent_command["params"]["samples"] == 128

@pytest.mark.asyncio
async def test_error_handling(client):
    """测试错误处理"""
    # 测试连接错误
    with pytest.raises(ConnectionError):
        await client._send_command("test", {})
    
    # 测试验证错误
    with pytest.raises(ValidationError):
        await client._validate_request("invalid_endpoint", {}) 