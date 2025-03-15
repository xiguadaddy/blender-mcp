"""
BlenderMCP Client

This module implements the client for connecting to a BlenderMCP server.
"""

import json
import asyncio
import logging
import websockets
from typing import Any, Dict, Optional, Union, List

from .protocol.commands import *

logger = logging.getLogger(__name__)

class BlenderMCPClient:
    """BlenderMCP client implementation"""
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        """Initialize the client
        
        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.websocket = None
        
    async def connect(self):
        """Connect to the server"""
        uri = f"ws://{self.host}:{self.port}"
        try:
            self.websocket = await websockets.connect(uri)
            logger.info(f"Connected to {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to {uri}: {e}")
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
            
        message = {
            "command": command,
            "params": params or {}
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            raise
            
    # 场景操作
    async def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene"""
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
        return await self.send_command(DELETE_OBJECT, {PARAM_NAME: name})
    
    async def get_object_info(self, name: str) -> Dict[str, Any]:
        """Get information about an object"""
        return await self.send_command(GET_OBJECT_INFO, {PARAM_NAME: name})
    
    # 材质操作
    async def set_material(
        self,
        object_name: str,
        material_name: Optional[str] = None,
        color: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Set or create a material for an object"""
        params = {PARAM_NAME: object_name}
        if material_name:
            params[PARAM_MATERIAL_NAME] = material_name
        if color:
            params[PARAM_COLOR] = color
        return await self.send_command(SET_MATERIAL, params)
    
    async def set_texture(
        self,
        object_name: str,
        texture_id: str
    ) -> Dict[str, Any]:
        """Apply a texture to an object"""
        params = {
            PARAM_NAME: object_name,
            PARAM_TEXTURE_ID: texture_id
        }
        return await self.send_command(SET_TEXTURE, params) 