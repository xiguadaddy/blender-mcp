"""
BlenderMCP Server Implementation

This module implements the WebSocket server for BlenderMCP.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Callable, Awaitable, Optional
from ..common.protocol import Command, Response, ErrorCodes
from ..common.errors import BlenderMCPError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommandRegistry:
    """Registry for command handlers"""
    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}

    def register(self, command: str, handler: Callable[[Dict[str, Any]], Awaitable[Any]]):
        """Register a command handler"""
        self._handlers[command] = handler

    def get_handler(self, command: str) -> Optional[Callable[[Dict[str, Any]], Awaitable[Any]]]:
        """Get handler for a command"""
        return self._handlers.get(command)

class BlenderMCPServer:
    """BlenderMCP WebSocket Server"""
    def __init__(self, host: str = "localhost", port: int = 9876):
        self.host = host
        self.port = port
        self.command_registry = CommandRegistry()
        self._server = None

    async def handle_client(self, websocket, path):
        """Handle client connection"""
        try:
            async for message in websocket:
                try:
                    # Parse command
                    data = json.loads(message)
                    command = Command(**data)
                    
                    # Get handler
                    handler = self.command_registry.get_handler(command.command)
                    if not handler:
                        response = Response.error(
                            ErrorCodes.INVALID_COMMAND,
                            f"Unknown command: {command.command}",
                            command_id=command.id
                        )
                    else:
                        try:
                            # Execute handler
                            result = await handler(command.params)
                            response = Response.success(result, command_id=command.id)
                        except BlenderMCPError as e:
                            response = Response.error(
                                e.code,
                                str(e),
                                e.details,
                                command_id=command.id
                            )
                        except Exception as e:
                            logger.exception("Error executing command")
                            response = Response.error(
                                ErrorCodes.EXECUTION_ERROR,
                                str(e),
                                command_id=command.id
                            )
                    
                    # Send response
                    await websocket.send(response.to_json())
                
                except json.JSONDecodeError:
                    response = Response.error(
                        ErrorCodes.INVALID_COMMAND,
                        "Invalid JSON format"
                    )
                    await websocket.send(response.to_json())
                except Exception as e:
                    logger.exception("Error processing message")
                    response = Response.error(
                        ErrorCodes.INTERNAL_ERROR,
                        str(e)
                    )
                    await websocket.send(response.to_json())
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except Exception as e:
            logger.exception("Unexpected error in client handler")

    async def start(self):
        """Start the server"""
        self._server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info(f"Server started on ws://{self.host}:{self.port}")
        await self._server.wait_closed()

    async def stop(self):
        """Stop the server"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Server stopped") 