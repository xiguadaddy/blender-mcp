"""
BlenderMCP Protocol Definitions

This module defines the standard protocol for communication between the BlenderMCP client and server.
It includes command and response formats, as well as utility functions for protocol handling.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import uuid
import json

@dataclass
class Command:
    """Standard command format for BlenderMCP"""
    command: str
    params: Dict[str, Any]
    id: str
    version: str = "1.0"

    @classmethod
    def create(cls, command: str, params: Dict[str, Any]) -> 'Command':
        """Create a new command instance with a unique ID"""
        return cls(
            command=command,
            params=params,
            id=str(uuid.uuid4()),
            version="1.0"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary format"""
        return {
            "command": self.command,
            "params": self.params,
            "id": self.id,
            "version": self.version
        }

    def to_json(self) -> str:
        """Convert command to JSON string"""
        return json.dumps(self.to_dict())

@dataclass
class ErrorInfo:
    """Error information structure"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to dictionary format"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details or {}
        }

@dataclass
class Response:
    """Standard response format for BlenderMCP"""
    status: str  # "success" or "error"
    data: Optional[Any] = None
    error: Optional[ErrorInfo] = None
    id: Optional[str] = None

    @classmethod
    def success(cls, data: Any, command_id: Optional[str] = None) -> 'Response':
        """Create a success response"""
        return cls(
            status="success",
            data=data,
            id=command_id
        )

    @classmethod
    def error(cls, code: str, message: str, details: Optional[Dict[str, Any]] = None, 
              command_id: Optional[str] = None) -> 'Response':
        """Create an error response"""
        return cls(
            status="error",
            error=ErrorInfo(code=code, message=message, details=details),
            id=command_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format"""
        result = {
            "status": self.status,
            "id": self.id
        }
        if self.status == "success":
            result["data"] = self.data
        else:
            result["error"] = self.error.to_dict() if self.error else None
        return result

    def to_json(self) -> str:
        """Convert response to JSON string"""
        return json.dumps(self.to_dict())

# Error codes
class ErrorCodes:
    """Standard error codes for BlenderMCP"""
    INVALID_COMMAND = "INVALID_COMMAND"
    INVALID_PARAMS = "INVALID_PARAMS"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BLENDER_ERROR = "BLENDER_ERROR" 