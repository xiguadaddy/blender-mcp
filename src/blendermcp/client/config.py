"""
BlenderMCP Client Configuration System

This module provides configuration management and tool registration for BlenderMCP client.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ToolDefinition:
    """工具定义类"""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None

class MCPConfig:
    """MCP客户端配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "mcp.json"
        self.tools: Dict[str, ToolDefinition] = {}
        self.config: Dict[str, Any] = {}
        self._load_config()
        
    def _load_config(self):
        """加载配置文件"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"已加载配置文件: {self.config_path}")
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {self.config_path}")
                self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config = self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "host": "localhost",
            "port": 9876,
            "debug": False,
            "tools": {
                "basic": {
                    "enabled": True,
                    "parameters": {}
                },
                "advanced": {
                    "enabled": True,
                    "parameters": {
                        "max_quality": 1.0,
                        "use_gpu": True
                    }
                }
            }
        }
        
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            
    def register_tool(self, tool: ToolDefinition):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"已注册工具: {tool.name}")
        
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self.tools.get(name)
        
    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        """列出所有可用工具"""
        if category:
            return [tool for tool in self.tools.values() if tool.category == category]
        return list(self.tools.values())
        
    def get_tool_categories(self) -> List[str]:
        """获取所有工具类别"""
        return list(set(tool.category for tool in self.tools.values()))
        
    def is_tool_enabled(self, tool_name: str) -> bool:
        """检查工具是否启用"""
        tool_config = self.config.get("tools", {}).get(tool_name, {})
        return tool_config.get("enabled", True)
        
    def get_tool_parameters(self, tool_name: str) -> Dict[str, Any]:
        """获取工具参数"""
        tool_config = self.config.get("tools", {}).get(tool_name, {})
        return tool_config.get("parameters", {}) 