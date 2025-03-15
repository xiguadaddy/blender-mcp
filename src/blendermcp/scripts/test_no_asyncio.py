#!/usr/bin/env python
"""
测试脚本，用于验证是否成功避免了asyncio导入

该脚本模拟Blender环境，测试插件是否能够在没有asyncio的情况下正常加载。
"""

import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("开始测试")
    
    # 模拟Blender环境，阻止asyncio导入
    sys.modules['asyncio'] = None
    sys.modules['_asyncio'] = None
    
    try:
        # 尝试导入插件模块
        logger.info("尝试导入插件模块")
        
        # 添加项目根目录到Python路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # 导入插件模块
        from blendermcp.addon import __init__
        logger.info("成功导入__init__.py")
        
        from blendermcp.addon import server_operators
        logger.info("成功导入server_operators.py")
        
        from blendermcp.addon import panels
        logger.info("成功导入panels.py")
        
        from blendermcp.addon import preferences
        logger.info("成功导入preferences.py")
        
        from blendermcp.addon import operators
        logger.info("成功导入operators.py")
        
        from blendermcp.addon import properties
        logger.info("成功导入properties.py")
        
        logger.info("所有模块导入成功，测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 