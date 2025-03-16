# BlenderMCP 安装和使用指南

## 安装要求

- Blender 3.0 或更高版本
- Python 3.7 或更高版本（用于外部MCP服务器）
- 以下Python包（用于外部MCP服务器）：
  - websockets >= 12.0
  - asyncio >= 3.4.3
  - jsonschema >= 4.17.3

## 安装步骤

### 方法1：通过Blender插件安装器

1. 下载最新的BlenderMCP插件ZIP文件
2. 打开Blender
3. 进入 编辑 > 首选项 > 插件
4. 点击 "安装..." 按钮
5. 选择下载的ZIP文件
6. 启用插件（勾选复选框）

### 方法2：手动安装

1. 下载或克隆BlenderMCP仓库
2. 将`src/blendermcp`目录复制到Blender的插件目录：
   - Windows: `%APPDATA%\Blender Foundation\Blender\<版本>\scripts\addons`
   - macOS: `~/Library/Application Support/Blender/<版本>/scripts/addons`
   - Linux: `~/.config/blender/<版本>/scripts/addons`
3. 打开Blender
4. 进入 编辑 > 首选项 > 插件
5. 搜索"BlenderMCP"
6. 启用插件（勾选复选框）

### 安装外部依赖

BlenderMCP的MCP服务器需要在外部Python环境中运行，因此需要安装以下依赖：

```bash
pip install websockets>=12.0 asyncio>=3.4.3 jsonschema>=4.17.3
```

## 配置

### 服务器设置

1. 打开Blender
2. 进入 编辑 > 首选项 > 插件
3. 找到"BlenderMCP"插件并展开
4. 配置以下选项：
   - **服务器模式**：选择WebSocket或标准输入/输出
   - **主机**：设置WebSocket服务器主机名（默认为localhost）
   - **端口**：设置WebSocket服务器端口（默认为9876）
   - **自动启动**：选择是否在插件加载时自动启动MCP服务器

## 使用方法

### 启动MCP服务器

1. 打开Blender的3D视图
2. 在右侧边栏中找到"MCP"选项卡
3. 点击"启动服务器"按钮

### 连接到MCP服务器

#### WebSocket模式

1. 在MCP面板中启动服务器
2. 点击"复制URL"按钮复制WebSocket URL
3. 在支持MCP的客户端（如Claude或Cursor）中使用该URL进行连接

#### STDIO模式

STDIO模式主要用于直接在环境中启动客户端的场景，不需要额外的连接步骤。

### 停止MCP服务器

1. 在MCP面板中点击"停止服务器"按钮
2. 服务器状态将变为"已停止"

## 故障排除

### 常见问题

1. **插件无法启用**
   - 确保Blender版本为3.0或更高
   - 检查插件目录是否正确
   - 查看Blender控制台是否有错误信息

2. **服务器启动失败**
   - 确保已安装所需的Python依赖
   - 检查端口是否被占用
   - 查看日志文件获取详细错误信息

3. **WebSocket连接失败**
   - 确保服务器已启动
   - 检查主机和端口设置
   - 确认防火墙设置

### 日志文件位置

BlenderMCP生成以下日志文件：

- `blendermcp_addon.log` - 插件日志
- `mcp_server.log` - MCP服务器日志

这些文件位于系统临时目录中：
- Windows: `%TEMP%`
- macOS: `/tmp`
- Linux: `/tmp`

## 更新插件

### 通过Blender插件安装器更新

1. 下载最新的BlenderMCP插件ZIP文件
2. 打开Blender
3. 进入 编辑 > 首选项 > 插件
4. 找到"BlenderMCP"插件
5. 点击 "删除" 按钮移除旧版本
6. 点击 "安装..." 按钮
7. 选择下载的ZIP文件
8. 启用插件（勾选复选框）

### 手动更新

1. 下载或克隆最新的BlenderMCP仓库
2. 删除Blender插件目录中的旧版本
3. 将新版本的`src/blendermcp`目录复制到Blender的插件目录
4. 重启Blender
5. 确保插件已启用

## 卸载

1. 打开Blender
2. 进入 编辑 > 首选项 > 插件
3. 找到"BlenderMCP"插件
4. 取消勾选复选框禁用插件
5. 点击 "删除" 按钮完全移除插件

## 支持和反馈

如果您遇到问题或有改进建议，请通过以下方式联系我们：

- 提交GitHub Issue
- 发送电子邮件至support@blendermcp.org
- 加入我们的Discord社区 