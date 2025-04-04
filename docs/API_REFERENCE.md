# BlenderMCP API 参考文档

本文档详细说明了BlenderMCP的API指令，帮助语言模型精确控制Blender进行3D建模。

## 连接

BlenderMCP服务器默认在`localhost:9876`上运行，使用TCP套接字通信。所有命令和响应均为JSON格式。

## 命令格式

每个API调用使用以下JSON格式：

```json
{
  "type": "命令类型",
  "params": {
    "参数1": "值1",
    "参数2": "值2"
  }
}
```

服务器响应格式：

```json
{
  "status": "success|error",
  "result": {
    // 返回数据
  },
  "message": "如果出错，这里会有错误信息"
}
```

## 基础命令

### ping
测试服务器连接状态。

**请求**：
```json
{
  "type": "ping"
}
```

**响应**：
```json
{
  "status": "success",
  "result": {"pong": true}
}
```

### get_simple_info
获取Blender基本信息。

**请求**：
```json
{
  "type": "get_simple_info"
}
```

**响应**：
```json
{
  "status": "success",
  "result": {
    "blender_version": "3.6.0",
    "scene_name": "Scene",
    "object_count": 3
  }
}
```

### get_scene_info
获取当前场景的信息。

**请求**：
```json
{
  "type": "get_scene_info"
}
```

**响应**：包含场景名称及前10个物体的信息

## 物体操作命令

### create_object
创建新的3D对象。

**参数**：
- `type`: 对象类型，可选值: "CUBE", "SPHERE", "CYLINDER", "PLANE", "CONE", "TORUS", "EMPTY", "CAMERA", "LIGHT"
- `name`: (可选) 对象名称
- `location`: (可选) 位置坐标 [x, y, z]
- `rotation`: (可选) 欧拉角旋转 [x, y, z]
- `scale`: (可选) 缩放比例 [x, y, z]

**请求示例**：
```json
{
  "type": "create_object",
  "params": {
    "type": "CUBE",
    "name": "MyCube",
    "location": [0, 0, 0],
    "rotation": [0, 0, 0],
    "scale": [1, 1, 1]
  }
}
```

### modify_object
修改现有对象的属性。

**参数**：
- `name`: 要修改的对象名称
- `location`: (可选) 新位置
- `rotation`: (可选) 新旋转
- `scale`: (可选) 新缩放
- `visible`: (可选) 可见性

### delete_object
删除一个对象。

**参数**：
- `name`: 要删除的对象名称

### get_object_info
获取对象的详细信息。

**参数**：
- `name`: 对象名称

## 高级建模命令

### extrude_faces
挤出网格的特定面。

**参数**：
- `object_name`: 对象名称
- `face_indices`: 要挤出的面的索引数组
- `direction`: (可选) 挤出方向 [x, y, z]，默认使用面法线
- `distance`: 挤出距离，默认为1.0

**请求示例**：
```json
{
  "type": "extrude_faces",
  "params": {
    "object_name": "Cube",
    "face_indices": [0, 2],
    "direction": [0, 0, 1],
    "distance": 2.0
  }
}
```

### subdivide_mesh
细分网格。

**参数**：
- `object_name`: 对象名称
- `cuts`: 切割数量，默认为1
- `smooth`: 平滑强度，默认为0

### loop_cut
创建环切。

**参数**：
- `object_name`: 对象名称
- `cuts`: 环切数量，默认为1
- `edge_index`: (可选) 边索引，如不提供则需要用户干预
- `factor`: 环切位置因子(0.0-1.0)，默认为0.5

### apply_modifier
应用修改器到对象。

**参数**：
- `object_name`: 对象名称
- `modifier_type`: 修改器类型，如"SUBDIVISION", "MIRROR", "BEVEL"等
- `params`: 修改器特定参数

**请求示例**：
```json
{
  "type": "apply_modifier",
  "params": {
    "object_name": "Cube",
    "modifier_type": "SUBDIVISION",
    "params": {
      "levels": 2,
      "render_levels": 2
    }
  }
}
```

### set_vertex_position
精确设置顶点位置。

**参数**：
- `object_name`: 对象名称
- `vertex_indices`: 顶点索引数组
- `positions`: 对应的位置数组，每个位置为 [x, y, z]

### create_animation
创建关键帧动画。

**参数**：
- `object_name`: 对象名称
- `keyframes`: 关键帧字典，格式为 {"帧号": 值}
- `property_path`: 要动画化的属性路径，如"location", "rotation_euler", "scale"

**请求示例**：
```json
{
  "type": "create_animation",
  "params": {
    "object_name": "Cube",
    "keyframes": {
      "1": [0, 0, 0],
      "30": [0, 0, 5],
      "60": [0, 0, 0]
    },
    "property_path": "location"
  }
}
```

### create_node_material
创建基于节点的材质。

**参数**：
- `name`: 材质名称
- `node_setup`: 节点设置，包含nodes和links部分

### set_uv_mapping
设置UV映射。

**参数**：
- `object_name`: 对象名称
- `projection`: 投影类型，如"CUBE", "CYLINDER", "SPHERE", "PROJECT", "UNWRAP"
- `scale`: 比例，默认为[1, 1, 1]

### join_objects
合并多个对象。

**参数**：
- `objects`: 要合并的对象名称列表
- `target_object`: 合并后保留的对象名称（必须是objects列表中的一个）

**请求示例**：
```json
{
  "type": "join_objects",
  "params": {
    "objects": ["Cube1", "Cube2", "Sphere"],
    "target_object": "Cube1"
  }
}
```

**响应**：
```json
{
  "status": "success",
  "result": {
    "name": "Cube1",
    "type": "MESH",
    "vertices": 26
  }
}
```

### separate_mesh
分离网格组件。

**参数**：
- `object_name`: 对象名称
- `method`: 分离方法，可选值: "SELECTED", "MATERIAL", "LOOSE"

### create_text
创建3D文本对象。

**参数**：
- `text`: 文本内容
- `location`: (可选) 位置
- `size`: (可选) 大小
- `extrude`: (可选) 挤出程度
- `name`: (可选) 对象名称

### create_curve
创建曲线对象。

**参数**：
- `curve_type`: 曲线类型，默认为"BEZIER"
- `points`: 控制点信息
- `location`: (可选) 位置
- `name`: (可选) 对象名称

### create_particle_system
创建粒子系统。

**参数**：
- `object_name`: 要添加粒子系统的对象
- `settings`: (可选) 粒子系统设置

### advanced_lighting
创建高级灯光。

**参数**：
- `light_type`: 灯光类型，如"POINT", "SUN", "SPOT", "AREA"
- `name`: (可选) 灯光名称
- `location`: 位置 [x, y, z]
- `energy`: 能量/亮度
- `color`: 颜色RGB值 [r, g, b]
- `shadow`: (可选) 是否产生阴影，默认为True

**请求示例**：
```json
{
  "type": "advanced_lighting",
  "params": {
    "light_type": "AREA",
    "name": "工作区灯光",
    "location": [0, 0, 5],
    "energy": 50,
    "color": [1.0, 0.95, 0.9]
  }
}
```

**注意**：不同类型的灯光支持不同的参数：
- "POINT": 点光源，支持所有基本参数
- "SUN": 太阳光，支持基本参数
- "SPOT": 聚光灯，支持基本参数
- "AREA": 区域光，支持基本参数

### set_material
设置对象材质。

**参数**：
- `object_name`: 对象名称
- `material_name`: (可选) 材质名称
- `create_if_missing`: 如果材质不存在是否创建，默认为true
- `color`: (可选) 颜色 [r, g, b] 或 [r, g, b, a]

### render_scene
渲染当前场景。

**参数**：
- `output_path`: (可选) 输出文件路径
- `resolution_x`: (可选) X分辨率
- `resolution_y`: (可选) Y分辨率

### execute_code
执行任意Python代码（高级用户使用）。

**参数**：
- `code`: 要执行的Python代码

**注意**：此功能强大但有潜在风险，请谨慎使用。

## 错误处理

处理API响应时，应当始终验证响应的状态。所有响应均包含一个`status`字段，可能的值为：

- `success`: 命令成功执行
- `error`: 命令执行失败

如果状态为`error`，响应还将包含一个`message`字段，说明错误原因。

**最佳实践**:

1. **始终检查响应状态**:
   ```python
   response = client.send_command("create_object", {"type": "CUBE"})
   if response.get("status") == "error":
       print(f"错误: {response.get('message', '未知错误')}")
       return
   ```

2. **验证对象是否存在**:
   在进行可能依赖对象存在的操作前，验证对象是否在场景中：
   ```python
   verify_response = client.send_command("get_object_info", {"name": object_name})
   if verify_response.get("status") != "success":
       print(f"错误: 对象 {object_name} 不存在")
       return
   ```

3. **使用重试机制**:
   对于关键操作，可以实现简单的重试逻辑：
   ```python
   max_retries = 3
   for attempt in range(max_retries):
       response = client.create_object("CUBE", name="MyCube")
       if response.get("status") == "success":
           break
       print(f"警告: 尝试 {attempt+1}/{max_retries} 失败，正在重试...")
       time.sleep(0.5)  # 等待短暂时间后重试
   ```

4. **获取对象名称**:
   响应格式可能因命令类型而异，建议使用辅助函数提取对象名称：
   ```python
   def get_object_name(response):
       """从响应中获取对象名称，处理不同的响应格式"""
       if response is None:
           return None
           
       if isinstance(response, dict):
           if "status" in response and response["status"] == "error":
               return None
               
           if "result" in response and isinstance(response["result"], dict):
               if "name" in response["result"]:
                   return response["result"]["name"]
               if "object" in response["result"]:
                   return response["result"]["object"]
                   
           if "name" in response:
               return response["name"]
       
       return None
   ```

遵循这些最佳实践可以提高脚本的健壮性，使其能够更好地处理各种错误情况。
