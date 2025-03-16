## WebSocket服务器启动问题

### 问题描述

在尝试启动BlenderMCP的WebSocket服务器时，可能会遇到以下问题：

1. `ModuleNotFoundError: No module named 'asyncio'` - 导入asyncio模块失败
2. 循环导入问题导致服务器启动失败
3. 在没有Blender环境的情况下，模拟`bpy`模块可能导致问题
4. 工具列表无法正确生成或加载

### 解决方案

我们创建了一个简单的独立WebSocket服务器作为替代方案：

1. 使用`src/blendermcp/test/simple_server.py`启动一个基本的WebSocket服务器
2. 该服务器不依赖于Blender特定的模块
3. 正确处理了`asyncio`的导入和事件循环设置
4. 实现了基本的JSON-RPC请求处理
5. 提供了测试工具并保存工具列表到临时文件

### 使用方法

1. 运行`python src/blendermcp/test/simple_server.py`启动服务器
2. 服务器将监听`0.0.0.0:9876`
3. 使用`python src/blendermcp/test/test_websocket.py`测试连接
4. 工具列表将保存在临时目录的`blendermcp_tools.json`文件中

### 长期解决方案

为了从根本上解决这些问题，我们建议：

1. 重构服务器代码，避免循环导入
2. 将服务器代码与Blender特定代码分离
3. 确保正确处理模块导入顺序
4. 改进错误处理和日志记录
5. 使用更健壮的方式处理工具注册和调用

通过使用简单服务器作为参考，可以更好地理解WebSocket服务器的工作原理，并将这些原则应用到主服务器代码中。

## 服务器代码改进

我们对服务器代码进行了以下改进，使其更加健壮：

### 1. 导入和事件循环设置

- 确保`asyncio`模块首先导入，避免其他导入干扰
- 为Windows平台正确设置事件循环策略
- 保存原始模块状态，避免模块干扰

### 2. 错误处理

- 增强了错误处理和日志记录
- 添加了更详细的错误堆栈跟踪
- 改进了WebSocket连接关闭的处理

### 3. 命令行参数

- 添加了`--debug`参数，用于启用调试模式
- 记录更多启动信息，包括Python版本、平台和工作目录
- 改进了信号处理

### 4. 工具注册和调用

- 简化了工具注册和调用过程
- 改进了工具列表的生成和保存
- 提供了更好的默认工具

### 5. 清理工作

- 在服务器关闭时清理临时文件
- 确保资源正确释放

### 使用方法

```bash
# 启动WebSocket服务器，监听所有网络接口并启用调试模式
python src/blendermcp/server/run_mcp_server.py --host 0.0.0.0 --debug

# 启动WebSocket服务器，使用默认设置（localhost:9876）
python src/blendermcp/server/run_mcp_server.py

# 启动STDIO服务器
python src/blendermcp/server/run_mcp_server.py --mode stdio
```

### 测试

使用测试客户端测试服务器：

```bash
python src/blendermcp/test/test_websocket.py
```

如果需要更简单的服务器进行测试，可以使用：

```bash
python src/blendermcp/test/simple_server.py
```

## 重大导入问题的终极解决方案

如果在运行主服务器（`run_mcp_server.py`）时仍然遇到`import of asyncio halted; None in sys.modules`错误，可以尝试使用我们的简化版服务器作为替代解决方案。

### 问题描述

主服务器因为复杂的代码结构和导入依赖，可能在某些环境下出现`asyncio`模块导入中断的问题。这是Python导入机制中的一个较为棘手的问题，通常与循环导入、模块模拟和`sys.modules`修改有关。

### 解决方案：使用简化版服务器

我们创建了一个简化版的服务器脚本`run_mcp_server_simple.py`，它具有以下特点：

1. 确保`asyncio`在最开始导入，避免导入中断
2. 不导入任何Blender相关模块，避免循环依赖
3. 内置核心功能，不依赖外部模块
4. 提供与原服务器相同的基本功能
5. 改进的错误处理和日志记录

### 使用方法

```bash
# 启动简化版WebSocket服务器，监听所有网络接口并启用调试模式
python src/blendermcp/server/run_mcp_server_simple.py --host 0.0.0.0 --debug

# 使用默认配置启动（localhost:9876）
python src/blendermcp/server/run_mcp_server_simple.py
```

### 功能对比

简化版服务器包含以下核心功能：
- WebSocket服务器（与原服务器相同的端口和协议）
- JSON-RPC消息处理
- 基本工具注册和调用
- 工具列表生成和保存
- 服务器状态更新
- 错误处理和日志记录

它不包含以下功能：
- STDIO模式支持
- 复杂的工具导入系统
- Blender API集成
- 高级安全功能

### 实现细节

简化版服务器通过以下方式解决asyncio导入问题：

1. 将`asyncio`作为第一个导入模块
2. 避免使用`sys.modules`修改已存在的模块
3. 避免动态导入和路径修改
4. 使用内置的工具定义和处理函数
5. 简化类结构，减少依赖

### 长期解决方案

为了从根本上解决这个问题，我们建议：

1. 重构服务器代码，避免循环依赖
2. 将服务器代码与Blender特定代码完全分离
3. 使用更简单的工具注册和导入机制
4. 改进错误处理，提供更详细的错误信息
5. 采用更现代的异步编程实践

通过使用简化版服务器，您可以避开复杂的导入问题，同时仍然获得核心的MCP服务器功能。 