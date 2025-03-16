# BlenderMCP 工具开发指南

本指南将帮助您为BlenderMCP创建自定义工具，扩展其功能以满足特定需求。

## 工具概述

在BlenderMCP中，工具是通过MCP协议暴露给AI客户端的功能单元。每个工具都有：

- 唯一的名称
- 描述性文档
- 输入参数模式
- 处理函数

## 工具开发流程

### 1. 规划工具

首先，确定工具的功能和目的：

- 工具将执行什么操作？
- 需要哪些输入参数？
- 将返回什么结果？
- 如何处理错误情况？

### 2. 创建工具处理函数

工具处理函数是实现工具功能的核心。基本结构如下：

```python
async def my_tool_handler(params):
    """
    工具描述
    
    Args:
        params: 包含以下字段的字典
            param1: 参数1描述
            param2: 参数2描述
            
    Returns:
        包含结果的字典
    """
    # 参数验证
    if "required_param" not in params:
        raise ValueError("缺少必需参数: required_param")
    
    # 实现工具功能
    result = {}
    
    # 处理Blender操作
    # ...
    
    # 返回结果
    return result
```

### 3. 注册工具

创建工具处理函数后，需要将其注册到MCP适配器中：

```python
from blendermcp.mcp.adapter import MCPAdapter

# 创建适配器实例
adapter = MCPAdapter()

# 注册工具
adapter.register_tool("my_namespace.my_tool", my_tool_handler)
```

### 4. 定义输入模式

为了提供更好的客户端体验，应为工具定义输入模式：

```python
my_tool_handler.input_schema = {
    "type": "object",
    "properties": {
        "param1": {
            "type": "string",
            "description": "参数1描述"
        },
        "param2": {
            "type": "number",
            "description": "参数2描述"
        }
    },
    "required": ["param1"]
}
```

## Blender操作示例

以下是一些常见Blender操作的示例：

### 创建对象

```python
async def create_cube_handler(params):
    """创建立方体"""
    import bpy
    
    # 获取参数
    location = params.get("location", (0, 0, 0))
    size = params.get("size", 2.0)
    name = params.get("name", "Cube")
    
    # 创建立方体
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    
    # 获取创建的对象
    obj = bpy.context.active_object
    obj.name = name
    
    # 返回结果
    return {
        "name": obj.name,
        "location": tuple(obj.location),
        "dimensions": tuple(obj.dimensions)
    }
```

### 修改材质

```python
async def set_material_handler(params):
    """设置对象材质"""
    import bpy
    
    # 获取参数
    object_name = params.get("object")
    color = params.get("color", (1, 1, 1, 1))
    
    # 获取对象
    obj = bpy.data.objects.get(object_name)
    if not obj:
        raise ValueError(f"对象不存在: {object_name}")
    
    # 创建材质
    mat_name = f"{object_name}_material"
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    
    # 设置颜色
    principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if principled_bsdf:
        principled_bsdf.inputs[0].default_value = color
    
    # 分配材质
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    
    # 返回结果
    return {
        "object": object_name,
        "material": mat_name,
        "color": color
    }
```

### 渲染场景

```python
async def render_scene_handler(params):
    """渲染场景"""
    import bpy
    import tempfile
    import os
    import base64
    
    # 获取参数
    resolution_x = params.get("resolution_x", 1920)
    resolution_y = params.get("resolution_y", 1080)
    
    # 设置渲染参数
    bpy.context.scene.render.resolution_x = resolution_x
    bpy.context.scene.render.resolution_y = resolution_y
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_file.close()
    
    # 设置输出路径
    bpy.context.scene.render.filepath = temp_file.name
    
    # 渲染场景
    bpy.ops.render.render(write_still=True)
    
    # 读取渲染结果
    with open(temp_file.name, "rb") as f:
        image_data = f.read()
    
    # 删除临时文件
    os.unlink(temp_file.name)
    
    # 返回Base64编码的图像
    return {
        "image": base64.b64encode(image_data).decode("utf-8"),
        "format": "png",
        "resolution": (resolution_x, resolution_y)
    }
```

## 工具命名约定

为了保持一致性和可维护性，请遵循以下命名约定：

- 使用点号分隔的命名空间，例如：`blender.object.create`
- 使用小写字母和下划线
- 命名空间应反映功能类别
- 工具名称应清晰描述其功能

示例：
- `blender.object.create` - 创建对象
- `blender.object.modify` - 修改对象
- `blender.material.assign` - 分配材质
- `blender.scene.render` - 渲染场景
- `blender.animation.keyframe` - 添加关键帧

## 错误处理

良好的错误处理对于工具的可靠性至关重要：

1. **参数验证** - 始终验证必需参数是否存在且格式正确
2. **明确的错误消息** - 提供清晰的错误消息，帮助用户理解问题
3. **优雅的失败** - 在出现错误时，尽可能清理临时资源
4. **异常捕获** - 捕获并处理可能的异常，避免服务器崩溃

示例：

```python
async def my_tool_handler(params):
    try:
        # 参数验证
        if "required_param" not in params:
            raise ValueError("缺少必需参数: required_param")
        
        # 实现工具功能
        # ...
        
        # 返回结果
        return result
    
    except ValueError as e:
        # 处理参数错误
        raise ValueError(f"参数错误: {str(e)}")
    
    except Exception as e:
        # 处理其他错误
        import traceback
        error_details = traceback.format_exc()
        raise RuntimeError(f"工具执行错误: {str(e)}\n{error_details}")
```

## 测试工具

在注册工具之前，应该对其进行测试：

1. **单元测试** - 为工具创建单元测试，验证其在各种情况下的行为
2. **集成测试** - 测试工具与Blender的集成
3. **边缘情况** - 测试各种边缘情况和错误情况

## 文档

为工具提供详细的文档是非常重要的：

1. **函数文档字符串** - 包含工具描述、参数和返回值
2. **输入模式** - 定义清晰的输入参数模式
3. **示例** - 提供使用示例
4. **注意事项** - 说明任何限制或特殊考虑

## 最佳实践

1. **保持简单** - 每个工具应专注于单一功能
2. **性能优化** - 避免不必要的操作，优化性能
3. **状态管理** - 小心管理Blender的状态，避免意外修改
4. **用户反馈** - 提供清晰的进度和结果反馈
5. **版本兼容性** - 考虑不同Blender版本的兼容性

## 示例工具集

以下是一些可以实现的工具示例：

1. **对象操作**
   - 创建基本图元（立方体、球体、圆柱体等）
   - 修改对象属性（位置、旋转、缩放等）
   - 复制、删除对象

2. **材质和纹理**
   - 创建和分配材质
   - 设置材质属性
   - 导入和应用纹理

3. **场景管理**
   - 创建和管理场景
   - 设置环境和照明
   - 管理相机和视角

4. **动画和模拟**
   - 创建关键帧动画
   - 设置物理模拟
   - 管理动画时间线

5. **渲染控制**
   - 设置渲染参数
   - 执行渲染
   - 管理渲染输出

## 结论

通过开发自定义工具，您可以大大扩展BlenderMCP的功能，使其更好地满足特定需求。遵循本指南中的最佳实践，可以确保您的工具可靠、高效且易于使用。 