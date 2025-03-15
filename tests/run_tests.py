"""
BlenderMCP Test Runner

This script runs all BlenderMCP tests and generates a report.
"""

import os
import sys
import logging
import asyncio
import importlib.util
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_module_from_file(file_path):
    """从文件路径导入模块"""
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def load_test_modules():
    """加载所有测试模块"""
    test_dir = Path(__file__).parent
    test_files = [f for f in test_dir.glob("test_*.py") if f.name != "run_tests.py"]
    
    modules = []
    for test_file in test_files:
        try:
            # 从文件导入模块
            module = import_module_from_file(test_file)
            if hasattr(module, 'run_tests'):
                modules.append(module)
            else:
                logger.warning(f"Module {test_file.name} has no run_tests function")
        except Exception as e:
            logger.error(f"Error loading test module {test_file.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    return modules

async def run_all_tests():
    """运行所有测试"""
    # 加载测试模块
    test_modules = load_test_modules()
    if not test_modules:
        logger.error("No test modules found")
        return
    
    logger.info(f"Found {len(test_modules)} test modules")
    
    # 运行测试
    results = {}
    for module in test_modules:
        module_name = module.__name__
        logger.info(f"\nRunning tests from {module_name}")
        
        try:
            # 运行测试
            if asyncio.iscoroutinefunction(module.run_tests):
                await module.run_tests()
            else:
                module.run_tests()
            results[module_name] = "PASS"
        except Exception as e:
            logger.error(f"Error running tests in {module_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results[module_name] = "FAIL"
    
    # 显示总结
    logger.info("\nTest Summary:")
    logger.info("=" * 40)
    for module_name, result in results.items():
        logger.info(f"{module_name}: {result}")
    logger.info("=" * 40)
    
    # 检查是否有失败的测试
    if "FAIL" in results.values():
        logger.error("Some tests failed!")
        sys.exit(1)
    else:
        logger.info("All tests passed!")

if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1) 