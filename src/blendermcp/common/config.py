"""
BlenderMCP Configuration

This module manages configuration for both server and client components.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "localhost"
    port: int = 9876
    log_level: str = "INFO"
    max_connections: int = 5
    command_timeout: float = 30.0

@dataclass
class ClientConfig:
    """Client configuration"""
    host: str = "localhost"
    port: int = 9876
    log_level: str = "INFO"
    reconnect_attempts: int = 3
    reconnect_delay: float = 1.0
    command_timeout: float = 30.0

class Config:
    """Configuration manager"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "blendermcp_config.json"
        self.server = ServerConfig()
        self.client = ClientConfig()
        self._load_config()
        
    def _load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                # 更新服务器配置
                if 'server' in data:
                    for key, value in data['server'].items():
                        if hasattr(self.server, key):
                            setattr(self.server, key, value)
                            
                # 更新客户端配置
                if 'client' in data:
                    for key, value in data['client'].items():
                        if hasattr(self.client, key):
                            setattr(self.client, key, value)
            except Exception as e:
                print(f"Error loading config: {e}")
                
    def save_config(self):
        """Save configuration to file"""
        try:
            data = {
                'server': {
                    'host': self.server.host,
                    'port': self.server.port,
                    'log_level': self.server.log_level,
                    'max_connections': self.server.max_connections,
                    'command_timeout': self.server.command_timeout
                },
                'client': {
                    'host': self.client.host,
                    'port': self.client.port,
                    'log_level': self.client.log_level,
                    'reconnect_attempts': self.client.reconnect_attempts,
                    'reconnect_delay': self.client.reconnect_delay,
                    'command_timeout': self.client.command_timeout
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
            
    @staticmethod
    def create_default_config(config_file: str):
        """Create a new configuration file with default settings"""
        config = Config(config_file)
        config.save_config()
        return config 