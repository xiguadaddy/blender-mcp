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