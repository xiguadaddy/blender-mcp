"""
测试安全验证模块
"""

import pytest
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from blendermcp.server.security import SecurityValidator

class TestSecurityValidator:
    """测试安全验证器"""
    
    def test_init(self):
        """测试初始化"""
        validator = SecurityValidator()
        assert validator.safe_paths == []
        assert validator.resource_limits["max_objects"] > 0
        assert validator.resource_limits["max_vertices"] > 0
        assert validator.resource_limits["max_file_size"] > 0
        assert validator.resource_limits["max_memory"] > 0
        
    def test_add_safe_path(self):
        """测试添加安全路径"""
        validator = SecurityValidator()
        test_path = "/tmp/test"
        validator.add_safe_path(test_path)
        # 使用os.path.normpath来规范化路径进行比较
        assert os.path.normpath(test_path) in validator.safe_paths
        
    def test_is_safe_path(self):
        """测试路径安全检查"""
        validator = SecurityValidator()
        safe_path = "/tmp/safe"
        unsafe_path = "/tmp/unsafe"
        validator.add_safe_path(safe_path)
        
        # 测试安全路径
        assert validator.is_safe_path(safe_path) is True
        assert validator.is_safe_path(f"{safe_path}/file.txt") is True
        
        # 测试不安全路径
        assert validator.is_safe_path(unsafe_path) is False
        
        # 测试路径遍历攻击
        assert validator.is_safe_path(f"{safe_path}/../unsafe") is False
        
    def test_sanitize_string(self):
        """测试字符串清理"""
        validator = SecurityValidator()
        
        # 测试正常字符串
        normal = "test_string_123"
        assert validator.sanitize_string(normal) == normal
        
        # 测试包含特殊字符的字符串
        special = "test;rm -rf /;echo"
        sanitized = validator.sanitize_string(special)
        assert ";" not in sanitized
        
    def test_validate_object_name(self):
        """测试对象名称验证"""
        validator = SecurityValidator()
        
        # 测试有效名称
        assert validator.validate_object_name("Cube") is True
        assert validator.validate_object_name("Object_123") is True
        
        # 测试无效名称
        assert validator.validate_object_name("") is False
        assert validator.validate_object_name("Object;") is False
        assert validator.validate_object_name("../Object") is False
        
    def test_validate_resource_limits(self):
        """测试资源限制验证"""
        validator = SecurityValidator()
        
        # 设置资源限制
        validator.resource_limits["max_objects"] = 10
        validator.resource_limits["max_vertices"] = 1000
        
        # 测试有效资源使用
        assert validator.validate_resource_limits({"objects": 5, "vertices": 500}) is True
        
        # 测试超出限制 - 确保键名匹配
        assert validator.validate_resource_limits({"max_objects": 15, "max_vertices": 500}) is False

if __name__ == '__main__':
    pytest.main() 