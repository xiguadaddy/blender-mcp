"""
BlenderMCP Client

This module implements the client for connecting to a BlenderMCP server.
"""

import json
import asyncio
import logging
import uuid
import traceback
import websockets
from typing import Any, Dict, Optional, Union, List, Type
from pathlib import Path

from .config import MCPConfig, ToolDefinition
from .tools import ToolRegistry
from .protocol.commands import *

logger = logging.getLogger(__name__)

class BlenderMCPClient:
    """BlenderMCP client implementation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the client
        
        Args:
            config_path: Optional path to the configuration file
        """
        # 加载配置
        self.config = MCPConfig(config_path)
        # 注册工具
        self.tool_registry = ToolRegistry(self.config)
        # 设置连接参数
        self.host = self.config.config.get("host", "localhost")
        self.port = self.config.config.get("port", 9876)
        self.websocket = None
        
    async def connect(self):
        """Connect to the server"""
        uri = f"ws://{self.host}:{self.port}"
        try:
            self.websocket = await websockets.connect(uri)
            logger.info(f"Connected to {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to {uri}: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise
            
    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from server")
            
    async def send_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to the server
        
        Args:
            command: Command name
            params: Command parameters
            
        Returns:
            Server response
        """
        if not self.websocket:
            raise RuntimeError("Not connected to server")
            
        # 检查工具是否可用
        tool = self.config.get_tool(command)
        if tool and not self.config.is_tool_enabled(command):
            raise RuntimeError(f"Tool {command} is disabled in configuration")
            
        command_id = str(uuid.uuid4())
        message = {
            "id": command_id,
            "command": command,
            "params": params or {}
        }
        
        try:
            logger.debug(f"发送命令: {message}")
            await self.websocket.send(json.dumps(message))
            response = await self.websocket.recv()
            logger.debug(f"收到响应: {response}")
            
            response_data = json.loads(response)
            if response_data.get("error"):
                error = response_data["error"]
                logger.error(f"服务器返回错误: {error}")
                raise RuntimeError(error.get("message", "Unknown error"))
                
            return response_data.get("result", {})
            
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise
            
    def list_available_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有可用的工具
        
        Args:
            category: 可选的工具类别过滤器
            
        Returns:
            工具列表，每个工具包含名称、描述和参数信息
        """
        tools = self.config.list_tools(category)
        return [{
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameters": tool.parameters,
            "enabled": self.config.is_tool_enabled(tool.name)
        } for tool in tools]
        
    def get_tool_categories(self) -> List[str]:
        """获取所有工具类别"""
        return self.config.get_tool_categories()
        
    # 高级材质操作
    async def create_node_material(
        self,
        name: str,
        node_setup: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建节点材质"""
        params = {
            "name": name,
            "node_setup": node_setup
        }
        return await self.send_command("create_node_material", params)
        
    # 高级灯光操作
    async def create_light(
        self,
        type: str,
        name: Optional[str] = None,
        location: Optional[List[float]] = None,
        energy: Optional[float] = None,
        color: Optional[List[float]] = None,
        shadow: Optional[bool] = None
    ) -> Dict[str, Any]:
        """创建灯光"""
        params = {"type": type}
        if name:
            params["name"] = name
        if location:
            params["location"] = location
        if energy:
            params["energy"] = energy
        if color:
            params["color"] = color
        if shadow is not None:
            params["shadow"] = shadow
        return await self.send_command("create_light", params)
        
    # 渲染操作
    async def set_render_settings(
        self,
        engine: str,
        samples: int,
        resolution_x: int,
        resolution_y: int,
        use_gpu: bool = True
    ) -> Dict[str, Any]:
        """设置渲染参数"""
        params = {
            "engine": engine,
            "samples": samples,
            "resolution_x": resolution_x,
            "resolution_y": resolution_y,
            "use_gpu": use_gpu
        }
        return await self.send_command("set_render_settings", params)
        
    async def render_image(
        self,
        output_path: str,
        format: str = "PNG",
        quality: int = 90
    ) -> Dict[str, Any]:
        """渲染图像"""
        params = {
            "output_path": output_path,
            "format": format,
            "quality": quality
        }
        return await self.send_command("render_image", params)
        
    # 建模操作
    async def edit_mesh(
        self,
        object_name: str,
        operation: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """编辑网格"""
        params = {
            "object_name": object_name,
            "operation": operation,
            "parameters": parameters
        }
        return await self.send_command("edit_mesh", params)
        
    async def add_modifier(
        self,
        object_name: str,
        modifier_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """添加修改器"""
        params = {
            "object_name": object_name,
            "modifier_type": modifier_type,
            "parameters": parameters
        }
        return await self.send_command("add_modifier", params)
        
    # 动画操作
    async def create_animation(
        self,
        object_name: str,
        property_path: str,
        keyframes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建动画"""
        params = {
            "object_name": object_name,
            "property_path": property_path,
            "keyframes": keyframes
        }
        return await self.send_command("create_animation", params)
        
    async def setup_physics(
        self,
        object_name: str,
        physics_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """设置物理模拟"""
        params = {
            "object_name": object_name,
            "physics_type": physics_type,
            "parameters": parameters
        }
        return await self.send_command("setup_physics", params)

    # 场景操作
    async def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene"""
        logger.info("获取场景信息")
        return await self.send_command(GET_SCENE_INFO)
    
    # 对象操作
    async def create_object(
        self,
        type: str,
        name: Optional[str] = None,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Create a new object in the scene"""
        logger.info(f"创建对象: type={type}, name={name}")
        params = {
            PARAM_TYPE: type
        }
        if name:
            params[PARAM_NAME] = name
        if location:
            params[PARAM_LOCATION] = location
        if rotation:
            params[PARAM_ROTATION] = rotation
        if scale:
            params[PARAM_SCALE] = scale
        return await self.send_command(CREATE_OBJECT, params)
    
    async def delete_object(self, name: str) -> Dict[str, Any]:
        """Delete an object from the scene"""
        logger.info(f"删除对象: {name}")
        return await self.send_command(DELETE_OBJECT, {PARAM_NAME: name})
    
    async def get_object_info(self, name: str) -> Dict[str, Any]:
        """Get information about an object"""
        logger.info(f"获取对象信息: {name}")
        return await self.send_command(GET_OBJECT_INFO, {PARAM_NAME: name})
    
    # 材质操作
    async def set_material(
        self,
        object_name: str,
        material_name: Optional[str] = None,
        color: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Set or create a material for an object"""
        logger.info(f"设置材质: object={object_name}, material={material_name}")
        params = {"object": object_name}
        if material_name:
            params["material"] = material_name
        if color:
            params[PARAM_COLOR] = color
        return await self.send_command(SET_MATERIAL, params)
    
    async def set_texture(
        self,
        object_name: str,
        texture_id: str
    ) -> Dict[str, Any]:
        """Apply a texture to an object"""
        logger.info(f"设置纹理: object={object_name}, texture={texture_id}")
        params = {
            PARAM_NAME: object_name,
            PARAM_TEXTURE_ID: texture_id
        }
        return await self.send_command(SET_TEXTURE, params) 