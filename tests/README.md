# BlenderMCP 测试说明

## 测试环境设置

1. 确保已安装所有依赖：
```bash
pip install -r requirements.txt
```

2. 确保Blender已启动并运行BlenderMCP插件

## 运行测试

在项目根目录下运行：

```bash
python tests/run_tests.py
```

## 测试文件结构

- `test_config.json`: 测试配置文件
- `test_basic_operations.py`: 基本操作测试
- `run_tests.py`: 测试运行器

## 添加新测试

1. 创建新的测试文件，文件名以 `test_` 开头
2. 在文件中实现 `run_tests()` 函数
3. 新测试将自动被测试运行器发现和执行

## 测试日志

测试日志将显示在控制台，包含：
- 测试模块加载信息
- 每个测试的执行状态
- 错误和警告信息
- 测试结果摘要

## 注意事项

- 确保在运行测试前启动Blender和BlenderMCP插件
- 测试可能会修改Blender场景，请在测试前保存重要工作
- 如果测试失败，查看日志了解详细信息 