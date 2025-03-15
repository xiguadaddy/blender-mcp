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
import jsonschema

from .config import MCPConfig, ToolDefinition
from .tools import ToolRegistry
from .protocol.commands import *
from .errors import (
    MCPError, ErrorCategory, ErrorContent, create_error_response,
    ValidationError, ConnectionError, ExecutionError, ResourceError,
    PermissionError, TimeoutError, is_retriable_error
)
from .api_spec import (
    API_VERSION, APICategory, APIEndpoint, ENDPOINTS,
    get_endpoint, validate_version, get_deprecated_endpoints
)
from .connection import ConnectionPool

logger = logging.getLogger(__name__)

class BlenderMCPClient:
    """BlenderMCP client implementation"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9876,
        max_connections: int = 10,
        min_connections: int = 2,
        config_path: Optional[str] = None
    ):
        """Initialize the client
        
        Args:
            host: Server host
            port: Server port
            max_connections: Maximum number of connections
            min_connections: Minimum number of connections
            config_path: Path to configuration file
        """
        self.host = host
        self.port = port
        self.config = MCPConfig(config_path) if config_path else MCPConfig()
        self.tool_registry = ToolRegistry(self.config)
        self.api_version = API_VERSION
        self.connection_pool = ConnectionPool(
            host=host,
            port=port,
            max_size=max_connections,
            min_size=min_connections
        )
        self._is_connected = False
        self._setup_default_tools()
        
    def _setup_default_tools(self) -> None:
        """设置默认工具"""
        # 注册所有API端点作为工具
        for endpoint in ENDPOINTS.values():
            self.tool_registry.register_tool(ToolDefinition(
                name=endpoint.name,
                description=endpoint.description,
                category=endpoint.category.value,
                parameters=endpoint.input_schema,
                handler=getattr(self, f"_handle_{endpoint.name}", None)
            ))
            
    async def start(self):
        """启动客户端"""
        try:
            await self.connection_pool.start()
            self._is_connected = True
            logger.info(f"客户端已启动: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"客户端启动失败: {e}")
            raise
        
    async def stop(self):
        """停止客户端"""
        try:
            await self.connection_pool.stop()
            self._is_connected = False
            logger.info("客户端已停止")
        except Exception as e:
            logger.error(f"客户端停止失败: {e}")
            raise
        
    async def _validate_request(self, endpoint_name: str, params: Dict[str, Any]) -> bool:
        """验证API请求"""
        endpoint = get_endpoint(endpoint_name)
        if not endpoint:
            raise ValidationError(f"未知的API端点: {endpoint_name}")
            
        if endpoint.deprecated:
            logger.warning(f"API端点 {endpoint_name} 已废弃")
            
        if endpoint.input_schema:
            try:
                logger.debug(f"验证请求参数: endpoint={endpoint_name}, params={params}, schema={endpoint.input_schema}")
                jsonschema.validate(instance=params, schema=endpoint.input_schema)
                logger.debug("参数验证成功")
                return True
            except jsonschema.exceptions.ValidationError as e:
                logger.error(f"参数验证失败: endpoint={endpoint_name}, params={params}, error={str(e)}")
                raise ValidationError(f"参数验证失败: {str(e)}")
        return True
        
    async def _handle_error(self, error: Exception, category: ErrorCategory) -> Dict[str, Any]:
        """处理错误并返回标准错误响应"""
        mcp_error = MCPError.from_exception(error, category)
        
        # 对于可重试的错误，尝试重试
        if is_retriable_error(category) and mcp_error.retry_count < mcp_error.max_retries:
            try:
                mcp_error.retry_count += 1
                logger.info(f"重试操作 (第{mcp_error.retry_count}次)")
                # 这里可以添加重试逻辑
                await asyncio.sleep(1)  # 简单的重试延迟
                return {"retrying": True, "retry_count": mcp_error.retry_count}
            except Exception as retry_error:
                logger.error(f"重试失败: {retry_error}")
                
        return mcp_error.to_dict()

    async def _handle_set_material(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理设置材质请求"""
        try:
            response = await self._send_command("set_material", params)
            if isinstance(response, dict) and response.get("isError"):
                return response
            return {
                "content": [{
                    "type": "text",
                    "text": f"材质设置成功: {response}"
                }]
            }
        except Exception as e:
            return await self._handle_error(e, ErrorCategory.EXECUTION)
        
    async def _send_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送命令到服务器"""
        try:
            # 验证API请求
            await self._validate_request(command, params)
            
            # 获取连接
            connection = await self.connection_pool.get_connection()
            try:
                message = {
                    "command": command,
                    "params": params,
                    "version": self.api_version
                }
                
                await connection.send(json.dumps(message))
                response = await connection.recv()
                return json.loads(response)
            finally:
                # 释放连接
                await self.connection_pool.release_connection(connection)
        except ValidationError as e:
            return await self._handle_error(e, ErrorCategory.VALIDATION)
        except asyncio.TimeoutError as e:
            return await self._handle_error(e, ErrorCategory.TIMEOUT)
        except Exception as e:
            return await self._handle_error(e, ErrorCategory.EXECUTION)
            
    def get_connection_stats(self) -> Dict[str, int]:
        """获取连接池统计信息"""
        return self.connection_pool.get_stats()

    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出可用工具"""
        tools = self.tool_registry.list_tools(category)
        return [tool.to_dict() for tool in tools]
        
    def list_available_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有可用的工具
        
        Args:
            category: 可选的工具类别过滤器
            
        Returns:
            工具列表，每个工具包含名称、描述和参数信息
        """
        tools = self.tool_registry.list_tools(category)
        return [{
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameters": tool.parameters,
            "enabled": self.tool_registry.is_tool_enabled(tool.name)
        } for tool in tools]
        
    def get_tool_categories(self) -> List[str]:
        """获取所有工具类别"""
        return self.tool_registry.get_tool_categories()
        
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
        return await self._send_command("create_node_material", params)
        
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
        return await self._send_command("create_light", params)
        
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
        return await self._send_command("set_render_settings", params)
        
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
        return await self._send_command("render_image", params)
        
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
        return await self._send_command("edit_mesh", params)
        
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
        return await self._send_command("add_modifier", params)
        
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
        return await self._send_command("create_animation", params)
        
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
        return await self._send_command("setup_physics", params)

    # 场景操作
    async def get_scene_info(self) -> Dict[str, Any]:
        """获取场景信息"""
        return await self._send_command("get_scene_info", {})
    
    # 对象操作
    async def create_object(
        self,
        object_type: str,
        object_name: Optional[str] = None,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """创建对象
        
        Args:
            object_type: 对象类型 (MESH, CURVE, LIGHT, CAMERA)
            object_name: 对象名称
            location: 位置坐标 [x, y, z]
            rotation: 旋转角度 [x, y, z]
            scale: 缩放比例 [x, y, z]
            
        Returns:
            包含创建结果的字典
        """
        params = {"object_type": object_type}
        if object_name:
            params["object_name"] = object_name
        if location:
            params["location"] = location
        if rotation:
            params["rotation"] = rotation
        if scale:
            params["scale"] = scale
            
        result = await self._send_command("create_object", params)
        logger.debug(f"创建对象结果: {result}")
        if "result" in result and "name" in result["result"]:
            return result
        return result
    
    async def delete_object(self, object_name: str) -> Dict[str, Any]:
        """删除对象"""
        params = {"object_name": object_name}
        return await self._send_command("delete_object", params)
    
    async def get_object_info(self, object_name: str) -> Dict[str, Any]:
        """获取对象信息"""
        try:
            if not object_name:
                raise ValidationError("对象名称不能为空")
            params = {"object_name": object_name}
            return await self._send_command("get_object_info", params)
        except Exception as e:
            return await self._handle_error(e, ErrorCategory.VALIDATION)
    
    # 材质操作
    async def set_material(
        self,
        object_name: str,
        material_name: Optional[str] = None,
        color: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """设置对象材质"""
        try:
            params = {"object_name": object_name}
            if material_name:
                params["material_name"] = material_name
            if color:
                params["color"] = color
                
            # 验证参数
            if not object_name:
                raise ValidationError("对象名称不能为空")
            if color and (len(color) != 4 or not all(isinstance(x, (int, float)) for x in color)):
                raise ValidationError("颜色必须是包含4个数字的列表(RGBA)")
                
            return await self._handle_set_material(params)
        except Exception as e:
            return await self._handle_error(e, ErrorCategory.EXECUTION)
    
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
        return await self._send_command(SET_TEXTURE, params)

    # API端点处理方法
    async def _handle_create_object(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理创建对象请求"""
        try:
            response = await self._send_command("create_object", params)
            if isinstance(response, dict) and response.get("isError"):
                return response
            return {
                "content": [{
                    "type": "text",
                    "text": f"对象创建成功: {response}"
                }]
            }
        except Exception as e:
            return await self._handle_error(e, ErrorCategory.EXECUTION)
            
    async def _handle_create_light(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理创建灯光请求"""
        try:
            response = await self._send_command("create_light", params)
            if isinstance(response, dict) and response.get("isError"):
                return response
            return {
                "content": [{
                    "type": "text",
                    "text": f"灯光创建成功: {response}"
                }]
            }
        except Exception as e:
            return await self._handle_error(e, ErrorCategory.EXECUTION)
            
    async def _handle_render_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理渲染图像请求"""
        try:
            response = await self._send_command("render_image", params)
            if isinstance(response, dict) and response.get("isError"):
                return response
            return {
                "content": [{
                    "type": "text",
                    "text": f"图像渲染成功: {response}"
                }]
            }
        except Exception as e:
            return await self._handle_error(e, ErrorCategory.EXECUTION) 