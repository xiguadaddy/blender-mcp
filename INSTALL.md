# BlenderMCP 安装指南

本指南将帮助您安装和配置BlenderMCP插件，使您能够通过MCP协议控制Blender。

## 系统要求

- Blender 2.80 或更高版本
- Python 3.7 或更高版本（通常随Blender一起安装）
- 网络连接（用于安装依赖项）

## 安装方法

### 方法一：从ZIP文件安装（推荐）

1. 下载最新的BlenderMCP ZIP文件
2. 在Blender中，导航到 `编辑 > 首选项 > 插件`
3. 点击 `安装...` 按钮
4. 找到并选择下载的ZIP文件
5. 勾选插件名称旁边的复选框以激活插件

安装过程会自动下载和安装所需的依赖项。如果您的Blender没有网络连接，请参考"离线安装"部分。

### 方法二：手动安装

1. 下载或克隆BlenderMCP仓库
   ```
   git clone https://github.com/yourusername/blender-mcp.git
   ```

2. 将 `src/blendermcp` 目录复制到Blender的插件目录：
   - Windows: `%APPDATA%\Blender Foundation\Blender\<版本>\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/<版本>/scripts/addons/`
   - Linux: `~/.config/blender/<版本>/scripts/addons/`

3. 安装依赖项：
   ```
   pip install -r requirements.txt
   ```

4. 在Blender中，导航到 `编辑 > 首选项 > 插件`
5. 找到并勾选"BlenderMCP"插件

## 离线安装依赖项

如果您的Blender环境没有网络连接，您可以预先下载依赖项并手动安装：

1. 在有网络连接的计算机上，使用以下命令下载依赖项：
   ```
   pip download -r requirements.txt -d ./dependencies
   ```

2. 将`dependencies`目录复制到Blender所在的计算机上

3. 在Blender的Python环境中安装依赖项：
   ```
   <Blender-Python路径> -m pip install --no-index --find-links=./dependencies -r requirements.txt
   ```

## 配置

安装后，您可以通过以下步骤配置BlenderMCP：

1. 在Blender中，导航到 `编辑 > 首选项 > 插件`
2. 找到"BlenderMCP"插件并点击展开
3. 设置以下选项：
   - **服务器模式**：选择"WebSocket"
   - **主机地址**：通常为`localhost`或`0.0.0.0`（允许远程连接）
   - **端口**：默认为`9876`，可根据需要更改
   - **自动启动服务器**：勾选此选项以在Blender启动时自动启动MCP服务器

## 验证安装

要验证BlenderMCP是否正确安装：

1. 在Blender的3D视图中，查找右侧面板（按N键显示）
2. 应该能看到"MCP"选项卡
3. 点击"启动服务器"按钮
4. 状态应显示为"已连接"

## 故障排除

如果安装过程中遇到问题：

1. **依赖项安装失败**：
   - 检查网络连接
   - 确认Python和pip已正确安装
   - 尝试手动安装依赖项（见上文）

2. **服务器启动失败**：
   - 检查端口是否被其他应用程序占用
   - 查看日志文件（在MCP面板中点击"查看日志"）
   - 确保防火墙未阻止连接

3. **找不到插件**：
   - 确认插件目录路径是否正确
   - 检查插件文件是否完整

4. **其他问题**：
   - 查看完整的日志文件（通常位于系统临时目录中的`blendermcp`文件夹）
   - 在GitHub上提交Issue

## 帮助与支持

如需更多帮助，请访问我们的文档或提交问题：

- 文档：[链接到文档]
- 问题跟踪：[链接到GitHub Issues]
- 社区论坛：[链接到论坛] 