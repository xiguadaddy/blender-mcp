"""
BlenderMCP Error Definitions

This module defines custom exceptions for BlenderMCP.
"""

from typing import Optional, Dict, Any
from .protocol import ErrorCodes

class BlenderMCPError(Exception):
    """Base exception for all BlenderMCP errors"""
    def __init__(self, message: str, code: str = ErrorCodes.INTERNAL_ERROR, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self):
        return self.message

class ConnectionError(BlenderMCPError):
    """Raised when there are connection issues"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCodes.CONNECTION_ERROR, details)

class CommandError(BlenderMCPError):
    """Raised when there are command-related issues"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCodes.INVALID_COMMAND, details)

class ParameterError(BlenderMCPError):
    """Raised when there are parameter-related issues"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCodes.INVALID_PARAMS, details)

class ExecutionError(BlenderMCPError):
    """Raised when there are execution-related issues"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCodes.EXECUTION_ERROR, details)

class BlenderError(BlenderMCPError):
    """Raised when there are Blender-specific issues"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCodes.BLENDER_ERROR, details)

class AuthError(BlenderMCPError):
    """身份验证相关的错误"""
    pass

class SecurityError(BlenderMCPError):
    """安全相关的错误"""
    pass

class ProtocolError(BlenderMCPError):
    """协议相关的错误"""
    pass

class ConfigError(BlenderMCPError):
    """配置相关的错误"""
    pass

class ResourceError(BlenderMCPError):
    """资源限制相关的错误"""
    pass

class BlenderAPIError(BlenderMCPError):
    """Blender API相关的错误"""
    pass

class MCPError(BlenderMCPError):
    """MCP协议操作相关的错误"""
    
    def __init__(self, message: str, code: int = -32000, data=None, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.code = code
        self.data = data 