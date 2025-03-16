# 贡献指南

感谢您对BlenderMCP项目的关注！我们欢迎各种形式的贡献，包括代码贡献、文档改进、问题报告和功能建议。本指南将帮助您了解如何参与到项目中来。

## 行为准则

参与本项目的所有贡献者都应遵循以下行为准则：

- 尊重所有参与者，不论其经验水平、性别、性取向、残疾状况、种族或宗教信仰
- 使用包容性语言
- 接受建设性批评
- 关注项目的最佳利益
- 对其他社区成员表示同理心

## 如何贡献

### 报告问题

如果您发现了bug或有功能建议，请通过GitHub Issues提交。在提交问题时，请包含以下信息：

1. **问题描述** - 清晰简洁地描述问题
2. **复现步骤** - 如何复现该问题的详细步骤
3. **预期行为** - 描述您期望看到的行为
4. **实际行为** - 描述实际发生的行为
5. **环境信息** - 包括：
   - Blender版本
   - 操作系统
   - BlenderMCP版本
   - Python版本
6. **截图或日志** - 如果适用，提供截图或日志文件

### 提交代码

1. **Fork仓库** - 在GitHub上Fork本仓库
2. **创建分支** - 为您的修改创建一个新分支
   ```
   git checkout -b feature/your-feature-name
   ```
   或
   ```
   git checkout -b fix/your-bugfix-name
   ```
3. **编写代码** - 进行您的修改，确保遵循代码规范
4. **提交更改** - 使用清晰的提交消息
   ```
   git commit -m "简明描述您的更改"
   ```
5. **推送到您的Fork** - 将更改推送到您的Fork
   ```
   git push origin feature/your-feature-name
   ```
6. **创建Pull Request** - 在GitHub上创建一个Pull Request到主仓库的main分支

### 代码规范

- 遵循PEP 8 Python代码风格指南
- 使用有意义的变量名和函数名
- 为函数和类添加文档字符串
- 保持代码简洁，避免不必要的复杂性
- 添加适当的注释解释复杂的逻辑
- 确保代码在Blender 3.0及以上版本中兼容

### 文档贡献

我们非常重视文档的改进。如果您想贡献文档：

1. 遵循与代码贡献相同的流程（Fork、分支、提交、Pull Request）
2. 确保文档清晰、准确且易于理解
3. 检查拼写和语法错误
4. 如果添加新功能，请确保更新相关文档

## 开发环境设置

1. **克隆仓库**
   ```
   git clone https://github.com/yourusername/blender-mcp.git
   cd blender-mcp
   ```

2. **安装依赖**
   ```
   pip install -r requirements.txt
   ```

3. **链接到Blender**
   
   将`src/blendermcp`目录链接或复制到Blender的插件目录：
   
   - Windows: `%APPDATA%\Blender Foundation\Blender\3.x\scripts\addons`
   - macOS: `~/Library/Application Support/Blender/3.x/scripts/addons`
   - Linux: `~/.config/blender/3.x/scripts/addons`

4. **启用插件**
   
   在Blender中，转到编辑 > 首选项 > 插件，搜索"BlenderMCP"并启用它。

## 测试

在提交代码之前，请确保：

1. 您的代码在Blender 3.0及以上版本中正常工作
2. MCP服务器能够正确启动和停止
3. WebSocket和STDIO通信模式都能正常工作
4. 所有工具功能都按预期运行
5. 用户界面元素显示正确且响应用户交互

## Pull Request流程

1. 确保您的PR描述清楚地说明了您所做的更改
2. 链接到相关的issue（如果有）
3. 更新相关文档（如果适用）
4. 确保所有自动化检查都通过
5. 等待维护者审查您的PR
6. 根据反馈进行必要的修改
7. 一旦获得批准，您的PR将被合并

## 版本控制

我们使用[语义化版本控制](https://semver.org/)。版本号格式为X.Y.Z：

- X: 主版本号，当进行不兼容的API更改时增加
- Y: 次版本号，当添加向后兼容的功能时增加
- Z: 修订号，当进行向后兼容的bug修复时增加

## 发布流程

1. 更新版本号（在`__init__.py`中）
2. 更新CHANGELOG.md
3. 创建一个新的发布标签
4. 构建发布包
5. 发布到GitHub Releases

## 社区

- 如果您有问题，请在GitHub Issues中提问
- 对于讨论和想法，请使用GitHub Discussions
- 关注项目更新，请Star本仓库

## 许可证

通过贡献您的代码，您同意您的贡献将在项目的许可证下发布。本项目使用MIT许可证。

---

再次感谢您对BlenderMCP项目的贡献！您的参与对于项目的成功至关重要。 