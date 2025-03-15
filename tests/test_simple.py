"""
简单测试模块
"""

import pytest
import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

def test_simple():
    """简单测试"""
    assert True

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 