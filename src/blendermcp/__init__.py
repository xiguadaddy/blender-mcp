"""
BlenderMCP Package

This package provides both client and addon implementations for BlenderMCP.
The client can be used independently without Blender dependencies.
"""

import os
import sys

# 添加依赖路径
addon_dir = os.path.dirname(os.path.abspath(__file__))
deps_dir = os.path.join(addon_dir, "deps")
if deps_dir not in sys.path:
    sys.path.append(deps_dir)

try:
    # 尝试导入addon模块（仅在Blender环境中可用）
    from .addon import register, unregister
except ImportError:
    # 在非Blender环境中，这些函数将不可用
    register = None
    unregister = None

# 总是导入客户端
from .client import BlenderMCPClient

__all__ = ['BlenderMCPClient', 'register', 'unregister']

# 版本信息
__version__ = '0.1.0' 