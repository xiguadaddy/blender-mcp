"""
BlenderMCP 安全验证模块

本模块提供安全验证和访问控制功能。
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class SecurityValidator:
    """安全验证器"""
    
    def __init__(self):
        """初始化安全验证器"""
        self.safe_paths = []
        self.resource_limits = {
            "max_objects": 1000,
            "max_vertices": 100000,
            "max_file_size": 100 * 1024 * 1024,  # 100MB
            "max_memory": 1024 * 1024 * 1024     # 1GB
        }
        
    def add_safe_path(self, path: str) -> None:
        """添加安全路径
        
        Args:
            path: 路径
        """
        normalized_path = os.path.normpath(path)
        if normalized_path not in self.safe_paths:
            self.safe_paths.append(normalized_path)
            logger.info(f"添加安全路径: {normalized_path}")
            
    def is_safe_path(self, path: str) -> bool:
        """检查路径是否安全
        
        Args:
            path: 路径
            
        Returns:
            是否安全
        """
        if not path:
            return False
            
        # 规范化路径
        normalized_path = os.path.normpath(path)
        
        # 检查是否在安全路径列表中
        for safe_path in self.safe_paths:
            if normalized_path == safe_path:
                return True
                
            # 检查是否是安全路径的子目录
            if normalized_path.startswith(safe_path + os.sep):
                # 防止路径遍历攻击
                relative_path = os.path.relpath(normalized_path, safe_path)
                if ".." not in relative_path.split(os.sep):
                    return True
                    
        return False
        
    def validate_resource_limits(self, resources: Dict[str, int]) -> bool:
        """验证资源限制
        
        Args:
            resources: 资源使用情况
            
        Returns:
            是否在限制范围内
        """
        for key, value in resources.items():
            # 检查是否是资源限制键
            limit_key = key if key in self.resource_limits else f"max_{key}"
            if limit_key in self.resource_limits and value > self.resource_limits[limit_key]:
                logger.warning(f"资源超出限制: {key}={value}, 限制={self.resource_limits[limit_key]}")
                return False
                
        return True
        
    def sanitize_string(self, input_str: str) -> str:
        """清理字符串，防止命令注入
        
        Args:
            input_str: 输入字符串
            
        Returns:
            清理后的字符串
        """
        if not input_str:
            return ""
            
        # 移除危险字符
        dangerous_chars = [';', '&', '|', '`', '$', '>', '<', '*', '?', '\\']
        result = input_str
        for char in dangerous_chars:
            result = result.replace(char, '')
            
        return result
        
    def validate_object_name(self, name: str) -> bool:
        """验证对象名称
        
        Args:
            name: 对象名称
            
        Returns:
            是否有效
        """
        if not name:
            return False
            
        # 检查是否包含危险字符
        if any(char in name for char in [';', '&', '|', '`', '$', '>', '<', '*', '?', '\\']):
            return False
            
        # 检查是否包含路径分隔符
        if '/' in name or '\\' in name:
            return False
            
        # 检查是否包含空格
        if ' ' in name:
            return False
            
        # 使用正则表达式验证
        pattern = r'^[a-zA-Z0-9_\-\.]+$'
        return bool(re.match(pattern, name))
        
    def validate_file_operation(self, path: str, operation: str) -> bool:
        """验证文件操作
        
        Args:
            path: 文件路径
            operation: 操作类型 (read, write, delete)
            
        Returns:
            是否允许操作
        """
        # 检查路径是否安全
        if not self.is_safe_path(path):
            logger.warning(f"不安全的文件路径: {path}")
            return False
            
        # 检查文件大小限制
        if operation in ['read', 'write'] and os.path.exists(path):
            file_size = os.path.getsize(path)
            if file_size > self.resource_limits['max_file_size']:
                logger.warning(f"文件大小超出限制: {file_size} > {self.resource_limits['max_file_size']}")
                return False
                
        return True
        
    def validate_command(self, command: str, params: Dict[str, Any]) -> bool:
        """验证命令和参数
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            是否允许执行
        """
        # 验证命令名称
        if not self.validate_object_name(command):
            logger.warning(f"无效的命令名称: {command}")
            return False
            
        # 验证对象名称参数
        if 'object_name' in params and not self.validate_object_name(params['object_name']):
            logger.warning(f"无效的对象名称: {params['object_name']}")
            return False
            
        # 验证文件路径参数
        if 'file_path' in params and not self.is_safe_path(params['file_path']):
            logger.warning(f"不安全的文件路径: {params['file_path']}")
            return False
            
        # 验证代码执行
        if command == 'execute_code' and 'code' in params:
            # 这里可以添加更复杂的代码分析
            dangerous_imports = ['os', 'subprocess', 'sys', 'shutil']
            code = params['code']
            for imp in dangerous_imports:
                if f"import {imp}" in code or f"from {imp}" in code:
                    logger.warning(f"代码包含危险导入: {imp}")
                    return False
                    
        return True
        
    def validate_parameters(self, params: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> bool:
        """验证参数
        
        Args:
            params: 参数
            rules: 参数规则
            
        Returns:
            是否有效
        """
        for param_name, rule in rules.items():
            # 检查必需参数
            if rule.get('required', False) and param_name not in params:
                logger.warning(f"缺少必需参数: {param_name}")
                return False
                
            # 如果参数不存在且不是必需的，跳过
            if param_name not in params:
                continue
                
            param_value = params[param_name]
            
            # 类型检查
            if 'type' in rule and not isinstance(param_value, rule['type']):
                logger.warning(f"参数类型错误: {param_name}, 期望 {rule['type']}, 实际 {type(param_value)}")
                return False
                
            # 范围检查
            if 'min' in rule and param_value < rule['min']:
                logger.warning(f"参数值过小: {param_name}={param_value}, 最小值={rule['min']}")
                return False
                
            if 'max' in rule and param_value > rule['max']:
                logger.warning(f"参数值过大: {param_name}={param_value}, 最大值={rule['max']}")
                return False
                
            # 长度检查
            if 'length' in rule and hasattr(param_value, '__len__') and len(param_value) != rule['length']:
                logger.warning(f"参数长度错误: {param_name}, 期望长度 {rule['length']}, 实际长度 {len(param_value)}")
                return False
                
        return True 