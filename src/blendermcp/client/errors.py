"""BlenderMCP错误处理模块"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class ErrorCategory(Enum):
    """错误类别枚举"""
    VALIDATION = "validation"  # 参数验证错误
    CONNECTION = "connection"  # 连接错误
    EXECUTION = "execution"   # 执行错误
    RESOURCE = "resource"     # 资源错误
    PERMISSION = "permission" # 权限错误
    TIMEOUT = "timeout"      # 超时错误
    UNKNOWN = "unknown"      # 未知错误

@dataclass
class ErrorContent:
    """错误内容"""
    type: str = "text"
    text: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN
    details: Optional[Dict[str, Any]] = None

@dataclass
class MCPError:
    """MCP标准错误对象"""
    isError: bool = True
    content: List[ErrorContent] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.content is None:
            self.content = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "isError": True,
            "content": [
                {
                    "type": content.type,
                    "text": content.text,
                    "category": content.category.value,
                    **({"details": content.details} if content.details else {})
                }
                for content in self.content
            ]
        }

    @classmethod
    def from_exception(cls, e: Exception, category: ErrorCategory = ErrorCategory.UNKNOWN) -> 'MCPError':
        """从异常创建错误对象"""
        return cls(
            content=[
                ErrorContent(
                    text=str(e),
                    category=category,
                    details={"type": type(e).__name__}
                )
            ]
        )

class ValidationError(Exception):
    """参数验证错误"""
    category = ErrorCategory.VALIDATION

class ConnectionError(Exception):
    """连接错误"""
    category = ErrorCategory.CONNECTION

class ExecutionError(Exception):
    """执行错误"""
    category = ErrorCategory.EXECUTION

class ResourceError(Exception):
    """资源错误"""
    category = ErrorCategory.RESOURCE

class PermissionError(Exception):
    """权限错误"""
    category = ErrorCategory.PERMISSION

class TimeoutError(Exception):
    """超时错误"""
    category = ErrorCategory.TIMEOUT

def create_error_response(
    message: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建标准错误响应"""
    error = MCPError(
        content=[
            ErrorContent(
                text=message,
                category=category,
                details=details
            )
        ]
    )
    return error.to_dict()

def is_retriable_error(category: ErrorCategory) -> bool:
    """判断错误是否可重试"""
    return category in {
        ErrorCategory.CONNECTION,
        ErrorCategory.TIMEOUT,
        ErrorCategory.RESOURCE
    } 