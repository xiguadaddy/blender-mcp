# 解决方案计划

## 思路

为了解决 Blender Python 环境的限制，同时又要利用 `bpy` 包的功能，我们可以考虑将 MCP 服务器的构建分为两个主要部分，并采用进程分离的架构：

1. **MCP 服务器核心 (Server Core):**
   -  使用独立的 Python 进程运行，这个进程**不依赖** `bpy`。
   -  可以使用最新的 `asyncio` 功能，实现 MCP 协议的核心逻辑，例如消息处理、工具注册、连接管理等。
   -  负责与外部 MCP 客户端进行网络通信（WebSocket 或 STDIO）。
   -  **不直接**操作 Blender 场景或数据。

2. **Blender 插件 (Blender Addon):**
   -  作为 Blender 的插件运行，**依赖** `bpy`。
   -  负责 Blender 内部的操作，例如场景修改、对象创建、属性设置等。
   -  通过某种进程间通信 (IPC) 机制与 MCP 服务器核心通信。
   -  将从 MCP 服务器核心接收到的指令转换为 `bpy` 操作，并执行。
   -  将 Blender 内部的状态和数据反馈给 MCP 服务器核心。


## 实现步骤概要:

1. **进程间通信 (IPC) 机制选择:**
   选择消息队列，我们先从改造 `src/blendermcp/addon/request_listener.py` 开始。这个文件负责 Blender 插件端的请求监听和消息处理，是改造 IPC 机制的关键入口点。
    a. **移除文件通信代码:**  删除 `REQUEST_FILE`, `RESPONSE_FILE` 常量以及所有与文件读写相关的代码。
    b. **引入消息队列:**  在 `request_listener.py` 中引入 `multiprocessing` 模块，并创建 `REQUEST_QUEUE` 和 `RESPONSE_QUEUE` 两个消息队列，用于 Blender 插件和 MCP 服务器核心之间的通信。
    c. **修改 `WebSocketClient`:**
        -  `WebSocketClient` 需要修改，使其不再读取和写入文件，而是将接收到的请求放入 `REQUEST_QUEUE`，并将响应从 `RESPONSE_QUEUE` 中取出并通过 WebSocket 发送。
        -  移除 `_handle_file_request` 和 `_handle_file_response` 等文件处理相关的方法。
        -  修改 `_process_messages` 方法，使其从 `REQUEST_QUEUE` 中获取请求，调用 `executor.process_request` 处理，并将结果放入 `RESPONSE_QUEUE`。
    d. **修改 `start()` 和 `stop()` 函数:**
        -  `start()` 函数需要负责初始化 `REQUEST_QUEUE` 和 `RESPONSE_QUEUE`。
        -  `stop()` 函数需要负责清理和关闭消息队列。

2. **MCP 服务器核心 (Server Core) 开发:**
   -  `src/blendermcp/server/` 目录下的代码可以作为 MCP 服务器核心的基础。
   -  需要确保 `run_mcp_server.py` 脚本在**不依赖 `bpy` 的独立 Python 环境**中可以正常运行。
   -  核心部分需要实现 MCP 协议的消息处理、工具注册和调度逻辑。
   -  工具的**实际执行**逻辑需要通过 IPC 传递给 Blender 插件。

3. **Blender 插件 (Blender Addon) 改造:**
   -  `src/blendermcp/addon/` 目录下的代码作为 Blender 插件的基础。
   -  `executor.py` 模块需要修改，使其不再直接执行 Blender 操作，而是将操作指令**序列化**并通过 IPC 发送给 MCP 服务器核心。
   -  `request_listener.py` 模块需要修改，使其负责监听来自 MCP 服务器核心的指令，并将指令**反序列化**后传递给 `executor.py` 执行。
   -  `panels.py`, `preferences.py`, `properties.py`, `tool_viewer.py`, `server_operators.py` 等模块主要负责 Blender 插件的用户界面和控制逻辑，可能需要根据 IPC 机制进行调整。

4. **工具模块 (Tools) 调整:**
   -  `src/blendermcp/tools/` 目录下的工具函数需要重新设计。
   -  可以将工具函数分为两类：
      -  **服务器端工具 (Server-side Tools):**  在 MCP 服务器核心中注册和调度，负责协议处理、参数验证等，**不包含 `bpy` 代码**。
      -  **Blender 端工具 (Blender-side Tools):**  在 Blender 插件中实现，**依赖 `bpy`**，负责实际的 Blender 操作。
   -  服务器端工具接收到客户端请求后，将请求参数和工具名称通过 IPC 发送给 Blender 插件，Blender 插件根据指令调用相应的 Blender 端工具执行操作，并将结果通过 IPC 返回给服务器端工具，最终返回给客户端。