"""
BlenderMCP 配置管理模块
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "config.yaml")
        self.config = self._load_default_config()
        
        # 如果配置文件存在，加载它
        if os.path.exists(self.config_path):
            self._load_config()
        else:
            # 否则创建默认配置文件
            self._save_config()
            
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置
        
        Returns:
            默认配置
        """
        return {
            "server": {
                "host": "localhost",
                "port": 9876,
                "max_connections": 10,
                "connection_timeout": 60
            },
            "security": {
                "safe_paths": [
                    os.path.join(os.path.expanduser("~"), "blender_projects")
                ],
                "resource_limits": {
                    "max_objects": 1000,
                    "max_vertices": 100000,
                    "max_file_size": 100 * 1024 * 1024,  # 100MB
                    "max_memory": 1024 * 1024 * 1024     # 1GB
                }
            },
            "auth": {
                "session_timeout": 3600,  # 1小时
                "permissions": {
                    "admin": ["*"],
                    "user": ["create_object", "delete_object", "get_object_info"]
                }
            },
            "logging": {
                "level": "INFO",
                "file": "blendermcp.log",
                "max_size": 10 * 1024 * 1024  # 10MB
            }
        }
        
    def _load_config(self) -> None:
        """从文件加载配置"""
        try:
            with open(self.config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    self._merge_config(self.config, loaded_config)
                    logger.info(f"已加载配置: {self.config_path}")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                logger.info(f"已保存配置: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """合并配置
        
        Args:
            base: 基础配置
            override: 覆盖配置
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
                
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，使用点号分隔，如 "server.host"
            default: 默认值
            
        Returns:
            配置值
        """
        parts = key.split('.')
        current = self.config
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            key: 配置键，使用点号分隔，如 "server.host"
            value: 配置值
        """
        parts = key.split('.')
        current = self.config
        
        # 遍历路径，直到最后一个部分
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
            
        # 设置最后一个部分的值
        current[parts[-1]] = value
        
        # 保存配置
        self._save_config()
        
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置
        
        Returns:
            所有配置
        """
        return self.config.copy() 