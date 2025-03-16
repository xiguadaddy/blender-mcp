# BlenderMCP

BlenderMCP是一个Blender插件，实现了Model Context Protocol (MCP)服务器，允许AI工具（如Claude和Cursor）与Blender进行通信，实现AI辅助的3D建模、动画和渲染功能。

![BlenderMCP Logo](docs/images/blendermcp_logo.png)

## 主要特性

- 支持WebSocket和标准输入/输出(STDIO)通信模式
- 完全兼容MCP协议规范
- 解决了Blender环境中的asyncio兼容性问题
- 支持动态工具注册和发现
- 提供完整的错误处理和日志记录
- 用户友好的界面，易于配置和使用

## 快速开始

### 安装

1. 下载最新的BlenderMCP插件ZIP文件
2. 打开Blender
3. 进入 编辑 > 首选项 > 插件
4. 点击 "安装..." 按钮
5. 选择下载的ZIP文件
6. 启用插件（勾选复选框）

### 使用

1. 打开Blender的3D视图
2. 在右侧边栏中找到"MCP"选项卡
3. 点击"启动服务器"按钮
4. 复制WebSocket URL
5. 在支持MCP的客户端中使用该URL进行连接

## 文档

- [安装和使用指南](docs/InstallationGuide.md)
- [MCP服务器实现](docs/MCPServer.md)
- [API参考](docs/APIReference.md)
- [工具开发指南](docs/ToolDevelopment.md)
- [优化计划](docs/UpdatePlan.md)

## 系统要求

- Blender 3.0 或更高版本
- Python 3.7 或更高版本（用于外部MCP服务器）
- 以下Python包（用于外部MCP服务器）：
  - websockets >= 12.0
  - asyncio >= 3.4.3
  - jsonschema >= 4.17.3

## 贡献

我们欢迎社区贡献！如果您想参与开发，请查看[贡献指南](CONTRIBUTING.md)。

## 许可证

本项目采用MIT许可证 - 详情请参阅[LICENSE](LICENSE)文件。

## 支持和反馈

如果您遇到问题或有改进建议，请通过以下方式联系我们：

- 提交GitHub Issue
- 发送电子邮件至support@blendermcp.org
- 加入我们的Discord社区

## 致谢

- Blender基金会 - 提供出色的3D创作软件
- Microsoft - 开发Model Context Protocol规范
- 所有贡献者和测试者
