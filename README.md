# BlenderMCP

BlenderMCP 是一个为Blender提供MCP（Minimal Capabilities Protocol）支持的项目，它允许您通过标准的通信协议远程控制和操作Blender。

## 项目架构

项目采用了进程分离的架构设计，以解决Blender Python环境限制的问题：

1. **MCP服务器核心 (Server Core)**：
   - 独立的Python进程运行，不依赖`bpy`
   - 使用最新的`asyncio`功能，实现MCP协议的核心逻辑
   - 负责与外部MCP客户端进行网络通信（WebSocket, HTTP或STDIO）
   - 不直接操作Blender场景或数据

2. **Blender插件 (Blender Addon)**：
   - 作为Blender的插件运行，依赖`bpy`
   - 负责Blender内部的操作，如场景修改、对象创建等
   - 通过进程间通信(IPC)机制与MCP服务器核心通信
   - 将接收到的指令转换为`bpy`操作并执行

3. **IPC机制**：
   - 使用`multiprocessing.Queue`实现进程间通信
   - 代替了早期版本中的文件通信方式
   - 提供更低延迟和更可靠的通信

## 安装方法

### 依赖条件

- Python 3.7+
- Blender 2.83+
- `websockets` Python库（用于WebSocket通信）

### 安装步骤

1. 克隆仓库:
   ```bash
   git clone https://github.com/yourusername/blendermcp.git
   cd blendermcp
   ```

2. 安装Python依赖:
   ```bash
   pip install -r requirements.txt
   ```

3. 安装Blender插件:
   - 启动Blender
   - 进入 Edit > Preferences > Add-ons
   - 点击 "Install"，选择 `blendermcp_addon.zip` 文件
   - 启用插件 "3D View: BlenderMCP"

## 使用方法

### 启动流程

1. **启动Blender并加载BlenderMCP插件**:
   - 运行Blender
   - 确保BlenderMCP插件已经启用

2. **在Blender中启动MCP监听器**:
   - 在Blender界面的侧边栏找到"BlenderMCP"面板
   - 点击"启动MCP监听器"按钮
   - 监听器将等待MCP服务器的连接

3. **启动MCP服务器核心**:
   - 在单独的终端窗口中，运行:
   ```bash
   python -m blendermcp.scripts.start_mcp_service --host 127.0.0.1 --port 5000
   ```
   - 服务器将通过IPC机制连接到Blender插件

4. **使用MCP客户端连接**:
   - 使用支持MCP协议的客户端连接到服务器
   - 连接地址: `ws://127.0.0.1:5000`
   - 可以调用注册的Blender工具执行操作

## 可用工具

BlenderMCP提供了多种工具函数，用于操作Blender：

### 对象工具
- `blender.create_cube` - 创建立方体
- `blender.create_sphere` - 创建球体
- `blender.create_cylinder` - 创建圆柱体
- `blender.transform_object` - 变换对象的位置、旋转和缩放
- `blender.delete_object` - 删除对象

### 场景工具
- `blender.create_camera` - 创建相机
- `blender.set_active_camera` - 设置活动相机
- `blender.create_light` - 创建光源

## 开发指南

### 添加新工具

要添加新的工具，需要遵循以下步骤：

1. 在`src/blendermcp/tools/`目录下创建或修改适当的工具模块
2. 定义两个函数：
   - `*_direct`函数：在Blender中直接执行的函数，依赖`bpy`
   - 异步函数：在服务器端调用，通过IPC转发请求到Blender
3. 在适当的`register_*_tools`函数中注册工具

例如：
```python
# 直接执行函数
def my_tool_direct(params):
    # 使用bpy执行操作
    return {"status": "success", "result": "..."}

# 服务器端函数
async def my_tool(params):
    return await request_blender_operation("my_tool", params)

# 注册函数
def register_tools(adapter):
    adapter.register_tool(
        "blender.my_tool",
        my_tool,
        "工具描述",
        [{"name": "param1", "type": "string", "description": "参数描述"}]
    )
```

## 贡献

欢迎提交Pull Request或Issue帮助改进项目。

## 许可

MIT License
