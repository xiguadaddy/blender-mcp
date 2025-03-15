"""
BlenderMCP MCP协议适配器

该模块提供了MCP协议适配器，用于在BlenderMCP和MCP客户端之间实现通信。
"""

import asyncio
import json
import logging
import sys
import traceback
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, Set, Tuple

from ..common.errors import ProtocolError

logger = logging.getLogger(__name__)

class MCPAdapter:
    """MCP协议适配器"""
    
    def __init__(self):
        """初始化MCP适配器"""
        self._tools: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._current_request_id: Optional[str] = None
        self._current_conversation_id: Optional[str] = None
        
    def register_tool(self, tool_name: str, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]) -> None:
        """注册工具处理器
        
        Args:
            tool_name: 工具名称
            handler: 工具处理器函数
        """
        self._tools[tool_name] = handler
        logger.debug(f"注册工具: {tool_name}")
        
    def register_prompt(self, prompt_id: str, prompt_data: Dict[str, Any]) -> None:
        """注册提示
        
        Args:
            prompt_id: 提示ID
            prompt_data: 提示数据
        """
        self._prompts[prompt_id] = prompt_data
        logger.debug(f"注册提示: {prompt_id}")
        
    async def handle_message(self, message: str) -> str:
        """处理MCP消息
        
        Args:
            message: 输入的JSON消息
            
        Returns:
            响应JSON消息
        """
        try:
            # 解析消息
            request = json.loads(message)
            
            if "method" not in request:
                raise ProtocolError("无效的JSON-RPC请求: 缺少方法字段")
                
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")
            
            self._current_request_id = request_id
            
            # 处理不同的方法
            if method == "mcp.initialize":
                return await self._handle_initialize(request_id, params)
                
            elif method == "mcp.getTools":
                return await self._handle_get_tools(request_id, params)
                
            elif method == "mcp.getPrompts":
                return await self._handle_get_prompts(request_id, params)
                
            elif method == "mcp.useTool":
                return await self._handle_use_tool(request_id, params)
                
            elif method == "mcp.usePrompt":
                return await self._handle_use_prompt(request_id, params)
                
            else:
                raise ProtocolError(f"未知的方法: {method}")
                
        except json.JSONDecodeError:
            return self._create_error_response("无效的JSON数据")
            
        except ProtocolError as e:
            return self._create_error_response(str(e))
            
        except Exception as e:
            logger.exception(f"处理MCP消息时出错: {e}")
            return self._create_error_response(f"内部错误: {str(e)}")
            
    async def _handle_initialize(self, request_id: str, params: Dict[str, Any]) -> str:
        """处理初始化请求
        
        Args:
            request_id: 请求ID
            params: 请求参数
            
        Returns:
            响应JSON字符串
        """
        try:
            client_info = params.get("client", {})
            conversation_id = params.get("conversationId")
            
            logger.info(f"客户端初始化: {client_info.get('name', '未知')} {client_info.get('version', '未知')}")
            self._current_conversation_id = conversation_id
            
            capabilities = {
                "protocolVersion": "0.1",
                "tools": True,
                "prompts": True,
                "abortCommand": True,
                "streamingTools": False  # 当前不支持流式工具
            }
            
            server_info = {
                "name": "BlenderMCP",
                "version": "0.1.0",  # 读取版本信息
                "capabilities": capabilities
            }
            
            return self._create_success_response(request_id, {
                "server": server_info
            })
            
        except Exception as e:
            logger.exception(f"处理初始化请求出错: {e}")
            return self._create_error_response(request_id, f"初始化错误: {str(e)}")
            
    async def _handle_get_tools(self, request_id: str, params: Dict[str, Any]) -> str:
        """处理获取工具请求
        
        Args:
            request_id: 请求ID
            params: 请求参数
            
        Returns:
            响应JSON字符串
        """
        try:
            # 构建工具列表
            tools = [
                {
                    "name": "blender.get_scene_info",
                    "description": "获取当前Blender场景的信息，包括对象、材质、相机等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "detailed": {
                                "type": "boolean",
                                "description": "是否返回详细的场景信息"
                            }
                        }
                    },
                    "returns": {
                        "type": "object",
                        "description": "返回场景信息对象"
                    }
                },
                {
                    "name": "blender.create_object",
                    "description": "在Blender场景中创建新对象",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "对象类型: MESH, LIGHT, CAMERA, EMPTY, CURVE",
                                "enum": ["MESH", "LIGHT", "CAMERA", "EMPTY", "CURVE"]
                            },
                            "name": {
                                "type": "string",
                                "description": "对象名称"
                            },
                            "location": {
                                "type": "array",
                                "description": "对象位置坐标 [x, y, z]",
                                "items": {"type": "number"}
                            },
                            "mesh_type": {
                                "type": "string",
                                "description": "网格类型(当type=MESH时): CUBE, SPHERE, CYLINDER, PLANE",
                                "enum": ["CUBE", "SPHERE", "CYLINDER", "PLANE"]
                            },
                            "light_type": {
                                "type": "string",
                                "description": "灯光类型(当type=LIGHT时): POINT, SUN, SPOT, AREA",
                                "enum": ["POINT", "SUN", "SPOT", "AREA"]
                            }
                        },
                        "required": ["type"]
                    },
                    "returns": {
                        "type": "object",
                        "description": "返回创建的对象信息"
                    }
                },
                {
                    "name": "blender.delete_object",
                    "description": "删除Blender场景中的对象",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "要删除的对象名称"
                            }
                        },
                        "required": ["name"]
                    },
                    "returns": {
                        "type": "object",
                        "description": "返回删除操作结果"
                    }
                },
                {
                    "name": "blender.set_material",
                    "description": "为Blender对象设置材质",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "object_name": {
                                "type": "string",
                                "description": "要设置材质的对象名称"
                            },
                            "material_name": {
                                "type": "string",
                                "description": "材质名称，如果为空则自动生成"
                            },
                            "create_new": {
                                "type": "boolean",
                                "description": "是否创建新材质，即使同名材质存在"
                            },
                            "color": {
                                "type": "array",
                                "description": "材质基础颜色 [r, g, b] 或 [r, g, b, a]，值范围0-1",
                                "items": {"type": "number"}
                            }
                        },
                        "required": ["object_name"]
                    },
                    "returns": {
                        "type": "object",
                        "description": "返回材质设置结果"
                    }
                },
                {
                    "name": "blender.render_image",
                    "description": "使用当前场景设置渲染图像",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "output_path": {
                                "type": "string",
                                "description": "输出文件路径，使用//开头表示相对于blend文件的路径"
                            },
                            "resolution_x": {
                                "type": "integer",
                                "description": "渲染分辨率宽度"
                            },
                            "resolution_y": {
                                "type": "integer",
                                "description": "渲染分辨率高度"
                            }
                        }
                    },
                    "returns": {
                        "type": "object",
                        "description": "返回渲染结果信息"
                    }
                }
            ]
            
            return self._create_success_response(request_id, {
                "tools": tools
            })
            
        except Exception as e:
            logger.exception(f"处理获取工具请求出错: {e}")
            return self._create_error_response(request_id, f"获取工具错误: {str(e)}")
            
    async def _handle_get_prompts(self, request_id: str, params: Dict[str, Any]) -> str:
        """处理获取提示请求
        
        Args:
            request_id: 请求ID
            params: 请求参数
            
        Returns:
            响应JSON字符串
        """
        try:
            # 返回注册的提示
            prompts = list(self._prompts.values())
            
            return self._create_success_response(request_id, {
                "prompts": prompts
            })
            
        except Exception as e:
            logger.exception(f"处理获取提示请求出错: {e}")
            return self._create_error_response(request_id, f"获取提示错误: {str(e)}")
            
    async def _handle_use_tool(self, request_id: str, params: Dict[str, Any]) -> str:
        """处理使用工具请求
        
        Args:
            request_id: 请求ID
            params: 请求参数
            
        Returns:
            响应JSON字符串
        """
        try:
            tool_name = params.get("name")
            tool_params = params.get("parameters", {})
            
            if not tool_name:
                return self._create_error_response(request_id, "缺少工具名称")
                
            # 查找工具处理器
            handler = self._tools.get(tool_name)
            
            if not handler:
                return self._create_error_response(request_id, f"未知的工具: {tool_name}")
                
            # 调用工具处理器
            result = await handler(tool_params)
            
            return self._create_success_response(request_id, result)
            
        except Exception as e:
            logger.exception(f"处理使用工具请求出错: {e}")
            error_details = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            return self._create_error_response(request_id, f"工具执行错误: {str(e)}", error_details=error_details)
            
    async def _handle_use_prompt(self, request_id: str, params: Dict[str, Any]) -> str:
        """处理使用提示请求
        
        Args:
            request_id: 请求ID
            params: 请求参数
            
        Returns:
            响应JSON字符串
        """
        try:
            prompt_id = params.get("id")
            
            if not prompt_id:
                return self._create_error_response(request_id, "缺少提示ID")
                
            # 查找提示
            prompt = self._prompts.get(prompt_id)
            
            if not prompt:
                return self._create_error_response(request_id, f"未知的提示: {prompt_id}")
                
            # 返回提示内容
            return self._create_success_response(request_id, {
                "content": prompt.get("content", [])
            })
            
        except Exception as e:
            logger.exception(f"处理使用提示请求出错: {e}")
            return self._create_error_response(request_id, f"提示执行错误: {str(e)}")
            
    def _create_success_response(self, request_id: str, result: Any) -> str:
        """创建成功响应
        
        Args:
            request_id: 请求ID
            result: 响应结果
            
        Returns:
            JSON字符串
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        
        return json.dumps(response)
        
    def _create_error_response(self, request_id: str, message: str, code: int = -32000, error_details: str = None) -> str:
        """创建错误响应
        
        Args:
            request_id: 请求ID
            message: 错误消息
            code: 错误代码
            error_details: 可选的详细错误信息
            
        Returns:
            JSON字符串
        """
        error = {
            "code": code,
            "message": message
        }
        
        if error_details:
            error["data"] = {"details": error_details}
            
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }
        
        return json.dumps(response) 