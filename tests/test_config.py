"""
测试配置管理模块
"""

import pytest
import os
import sys
import tempfile
import yaml
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from blendermcp.server.config import ConfigManager

class TestConfigManager:
    """测试配置管理器"""
    
    def setup_method(self):
        """测试前准备"""
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.yaml")
        
    def teardown_method(self):
        """测试后清理"""
        # 删除临时文件
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
        
    def test_init_default(self):
        """测试默认初始化"""
        config = ConfigManager(self.config_path)
        
        # 验证默认配置
        assert config.get("server.host") == "localhost"
        assert config.get("server.port") == 9876
        assert isinstance(config.get("security.resource_limits"), dict)
        assert isinstance(config.get("auth.permissions"), dict)
        
        # 验证配置文件已创建
        assert os.path.exists(self.config_path)
        
    def test_load_config(self):
        """测试加载配置"""
        # 创建测试配置文件
        test_config = {
            "server": {
                "host": "127.0.0.1",
                "port": 8080
            }
        }
        
        with open(self.config_path, "w") as f:
            yaml.dump(test_config, f)
            
        # 加载配置
        config = ConfigManager(self.config_path)
        
        # 验证配置已加载
        assert config.get("server.host") == "127.0.0.1"
        assert config.get("server.port") == 8080
        
        # 验证默认配置仍然存在
        assert isinstance(config.get("security.resource_limits"), dict)
        
    def test_get_config(self):
        """测试获取配置"""
        config = ConfigManager(self.config_path)
        
        # 测试获取存在的配置
        assert config.get("server.host") == "localhost"
        
        # 测试获取不存在的配置
        assert config.get("nonexistent.key") is None
        assert config.get("nonexistent.key", "default") == "default"
        
    def test_set_config(self):
        """测试设置配置"""
        config = ConfigManager(self.config_path)
        
        # 设置现有配置
        config.set("server.host", "192.168.1.1")
        assert config.get("server.host") == "192.168.1.1"
        
        # 设置新配置
        config.set("custom.key", "value")
        assert config.get("custom.key") == "value"
        
        # 设置嵌套配置
        config.set("custom.nested.key", "nested_value")
        assert config.get("custom.nested.key") == "nested_value"
        
        # 验证配置已保存到文件
        with open(self.config_path, "r") as f:
            saved_config = yaml.safe_load(f)
            assert saved_config["server"]["host"] == "192.168.1.1"
            assert saved_config["custom"]["key"] == "value"
            assert saved_config["custom"]["nested"]["key"] == "nested_value"
            
    def test_get_all(self):
        """测试获取所有配置"""
        config = ConfigManager(self.config_path)
        all_config = config.get_all()
        
        # 验证返回的是副本
        assert all_config is not config.config
        
        # 验证内容正确
        assert all_config["server"]["host"] == "localhost"
        assert all_config["server"]["port"] == 9876

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 