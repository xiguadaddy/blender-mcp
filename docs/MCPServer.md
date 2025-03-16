# MCP服务器实现

## 概述

BlenderMCP插件实现了Model Context Protocol (MCP)服务器，支持通过WebSocket和标准输入/输出(STDIO)两种通信模式。该服务器允许外部AI工具（如Claude和Cursor）与Blender进行通信，实现AI辅助的3D建模、动画和渲染功能。

## 架构设计

MCP服务器实现采用了模块化设计，主要包括以下组件：

1. **服务器核心** - 处理通信和消息路由
2. **适配器** - 连接Blender功能和MCP协议
3. **工具注册表** - 管理可用工具
4. **消息处理器** - 处理JSON-RPC消息

### 关键特性

- 支持WebSocket和STDIO通信模式
- 完全兼容MCP协议规范
- 解决了Blender环境中的asyncio兼容性问题
- 支持动态工具注册和发现
- 提供完整的错误处理和日志记录

## 实现细节

### 解决asyncio兼容性问题

Blender内置的Python环境对asyncio支持有限，为解决这一问题，我们采用了以下策略：

1. 在Blender插件中阻止asyncio导入：
   ```python
   import sys
   sys.modules['asyncio'] = None
   ```

2. 在单独的Python进程中运行MCP服务器，通过subprocess进行通信：
   ```python
   server_process = subprocess.Popen(
       [python_exe, script_path, "--mode", "websocket", "--host", host, "--port", str(port)],
       stdout=subprocess.PIPE,
       stderr=subprocess.PIPE,
       text=True
   )
   ```

3. 创建独立的服务器启动脚本，在外部Python环境中运行。

### 服务器启动脚本

服务器启动脚本(`run_mcp_server.py`)实现了完整的MCP服务器功能，包括：

- WebSocket服务器实现
- STDIO服务器实现
- JSON-RPC消息处理
- 工具注册和调用
- 错误处理和日志记录

### 通信流程

1. **WebSocket模式**：
   - 服务器在指定主机和端口上启动WebSocket服务器
   - 客户端通过WebSocket连接到服务器
   - 使用JSON-RPC协议进行通信

2. **STDIO模式**：
   - 服务器使用标准输入/输出进行通信
   - 消息使用Content-Length头进行分隔
   - 适用于直接在环境中启动客户端的场景

## 使用方法

### 在Blender中启动MCP服务器

1. 安装BlenderMCP插件
2. 打开Blender的MCP面板（位于3D视图的侧边栏）
3. 选择服务器模式（WebSocket或STDIO）
4. 如果选择WebSocket模式，设置主机和端口
5. 点击"启动服务器"按钮

### 配置选项

在BlenderMCP首选项中可以设置以下选项：

- **服务器模式**：WebSocket或标准输入/输出
- **主机**：WebSocket服务器主机名（默认为localhost）
- **端口**：WebSocket服务器端口（默认为9876）
- **自动启动**：插件加载时自动启动MCP服务器

### 连接到MCP服务器

#### WebSocket模式

1. 在MCP面板中启动服务器
2. 复制WebSocket URL（例如：`ws://localhost:9876`）
3. 在支持MCP的客户端中使用该URL进行连接

#### STDIO模式

STDIO模式主要用于直接在环境中启动客户端的场景，不需要额外的连接步骤。

## 工具开发

### 创建新工具

要创建新的MCP工具，需要实现以下步骤：

1. 创建工具处理函数：
   ```python
   async def my_tool_handler(params):
       # 实现工具功能
       return {"result": "工具执行结果"}
   ```

2. 注册工具：
   ```python
   adapter.register_tool("my.tool", my_tool_handler)
   ```

3. 提供工具描述和输入模式：
   ```python
   my_tool_handler.__doc__ = """
   我的工具描述
   
   Args:
       params: 工具参数
           
   Returns:
       工具结果
   """
   ```

### 工具命名约定

工具名称应使用点号分隔的命名空间，例如：

- `blender.object.create` - 创建Blender对象
- `blender.scene.render` - 渲染场景
- `blender.material.assign` - 分配材质

## 故障排除

### 常见问题

1. **服务器启动失败**
   - 检查端口是否被占用
   - 查看日志文件获取详细错误信息

2. **WebSocket连接失败**
   - 确保服务器已启动
   - 检查主机和端口设置
   - 确认防火墙设置

3. **工具调用失败**
   - 检查工具名称是否正确
   - 确认参数格式符合要求

### 日志文件位置

BlenderMCP生成以下日志文件：

- `blendermcp_addon.log` - 插件日志
- `mcp_server.log` - MCP服务器日志

这些文件位于系统临时目录中。

## 开发计划

未来的开发计划包括：

1. 扩展工具集，添加更多Blender功能
2. 改进性能和稳定性
3. 增强安全性
4. 提供更多示例和文档

## 参考资料

- [MCP协议规范](https://github.com/microsoft/modelcontextprotocol)
- [JSON-RPC 2.0规范](https://www.jsonrpc.org/specification)
- [WebSocket协议](https://datatracker.ietf.org/doc/html/rfc6455) 