import os
import sys

# 添加依赖路径
lib_path = os.path.join(os.path.dirname(__file__), "lib")
if os.path.exists(lib_path) and lib_path not in sys.path:
    sys.path.insert(0, lib_path)

"""
BlenderMCP Package

This package provides both client and addon implementations for BlenderMCP.
The client can be used independently without Blender dependencies.
"""

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