"""
BlenderMCP API 规范

本模块定义了BlenderMCP服务器API的标准格式。
"""

from typing import TypedDict, Union, Any, Optional, List, Dict

class APIRequest(TypedDict):
    """API请求格式"""
    command: str
    params: Dict[str, Any]
    id: Optional[str]

class APIResponse(TypedDict):
    """API响应格式"""
    id: Optional[str]
    success: bool
    result: Optional[Any]
    error: Optional[Dict[str, Any]]

class APIError(TypedDict):
    """API错误格式"""
    code: int
    message: str
    details: Optional[Dict[str, Any]]

# 标准参数命名
STANDARD_PARAMS = {
    # 通用参数
    'object_name': '对象名称',
    'object_type': '对象类型',
    'location': '位置 [x, y, z]',
    'rotation': '旋转 [x, y, z]',
    'scale': '缩放 [x, y, z]',
    'visible': '可见性',
    
    # 材质参数
    'material_name': '材质名称',
    'color': '颜色 [r, g, b, a]',
    'metallic': '金属度 (0-1)',
    'roughness': '粗糙度 (0-1)',
    'specular': '镜面反射 (0-1)',
    
    # 灯光参数
    'light_type': '灯光类型',
    'energy': '灯光能量',
    
    # 相机参数
    'focal_length': '焦距',
    'sensor_width': '传感器宽度'
}

# 标准响应格式
def create_response(
    id: Optional[str] = None,
    success: bool = True,
    result: Optional[Any] = None,
    error: Optional[Dict[str, Any]] = None
) -> APIResponse:
    """创建标准API响应"""
    return {
        'id': id,
        'success': success,
        'result': result,
        'error': error
    }

def create_error(
    code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> APIError:
    """创建标准错误对象"""
    return {
        'code': code,
        'message': message,
        'details': details
    }

# 错误代码定义
ERROR_CODES = {
    'INVALID_PARAMETER': 400,
    'OBJECT_NOT_FOUND': 404,
    'OPERATION_FAILED': 500,
    'TIMEOUT': 504
} 