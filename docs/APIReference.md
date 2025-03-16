# BlenderMCP API参考

本文档提供了BlenderMCP MCP服务器API的详细参考。

## 通信协议

BlenderMCP使用JSON-RPC 2.0协议通过WebSocket或标准输入/输出(STDIO)进行通信。

### 请求格式

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "方法名称",
    "params": {
        "参数1": "值1",
        "参数2": "值2"
    }
}
```

### 响应格式

成功响应：

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "字段1": "值1",
        "字段2": "值2"
    }
}
```

错误响应：

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32603,
        "message": "错误消息"
    }
}
```

## 核心方法

### initialize

初始化MCP服务器连接。

**请求**：

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {}
}
```

**响应**：

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "name": "BlenderMCP",
        "version": "0.1.0",
        "status": "ok"
    }
}
```

### shutdown

关闭MCP服务器连接。

**请求**：

```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "shutdown",
    "params": {}
}
```

**响应**：

```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "status": "ok"
    }
}
```

### listTools

获取可用工具列表。

**请求**：

```json
{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "listTools",
    "params": {}
}
```

**响应**：

```json
{
    "jsonrpc": "2.0",
    "id": 3,
    "result": {
        "tools": [
            {
                "name": "blender.object.create",
                "description": "创建Blender对象",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "对象类型"
                        },
                        "location": {
                            "type": "array",
                            "description": "对象位置"
                        }
                    },
                    "required": ["type"]
                }
            },
            {
                "name": "blender.scene.render",
                "description": "渲染场景",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "resolution_x": {
                            "type": "number",
                            "description": "水平分辨率"
                        },
                        "resolution_y": {
                            "type": "number",
                            "description": "垂直分辨率"
                        }
                    }
                }
            }
        ]
    }
}
```

### callTool

调用指定的工具。

**请求**：

```json
{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "callTool",
    "params": {
        "name": "blender.object.create",
        "params": {
            "type": "cube",
            "location": [0, 0, 0]
        }
    }
}
```

**响应**：

```json
{
    "jsonrpc": "2.0",
    "id": 4,
    "result": {
        "name": "Cube",
        "location": [0, 0, 0],
        "dimensions": [2, 2, 2]
    }
}
```

## 错误代码

BlenderMCP使用以下标准JSON-RPC 2.0错误代码：

| 代码 | 消息 | 描述 |
|------|------|------|
| -32700 | 解析错误 | 无效的JSON |
| -32600 | 无效请求 | 请求对象无效 |
| -32601 | 方法不存在 | 请求的方法不存在 |
| -32602 | 无效参数 | 无效的方法参数 |
| -32603 | 内部错误 | 内部JSON-RPC错误 |

此外，BlenderMCP还使用以下自定义错误代码：

| 代码 | 消息 | 描述 |
|------|------|------|
| -32000 | 服务器错误 | 通用服务器错误 |
| -32001 | 工具不存在 | 请求的工具不存在 |
| -32002 | 工具执行错误 | 工具执行过程中出错 |
| -32003 | Blender错误 | Blender操作错误 |

## 标准工具

以下是BlenderMCP提供的标准工具：

### blender.scene.info

获取当前场景信息。

**输入参数**：无

**返回值**：

```json
{
    "name": "场景名称",
    "objects": [
        {
            "name": "对象1",
            "type": "MESH",
            "location": [0, 0, 0]
        },
        {
            "name": "对象2",
            "type": "LIGHT",
            "location": [1, 1, 1]
        }
    ],
    "active_object": "当前活动对象名称",
    "frame_current": 1,
    "frame_start": 1,
    "frame_end": 250
}
```

### blender.object.create

创建新对象。

**输入参数**：

```json
{
    "type": "cube",  // 对象类型：cube, sphere, cylinder, plane, etc.
    "name": "MyCube",  // 可选，对象名称
    "location": [0, 0, 0],  // 可选，对象位置
    "rotation": [0, 0, 0],  // 可选，对象旋转
    "scale": [1, 1, 1],  // 可选，对象缩放
    "size": 2.0  // 可选，对象大小
}
```

**返回值**：

```json
{
    "name": "MyCube",
    "type": "MESH",
    "location": [0, 0, 0],
    "rotation": [0, 0, 0],
    "scale": [1, 1, 1],
    "dimensions": [2, 2, 2]
}
```

### blender.object.modify

修改现有对象。

**输入参数**：

```json
{
    "name": "对象名称",  // 要修改的对象名称
    "location": [1, 1, 1],  // 可选，新位置
    "rotation": [0, 0, 0],  // 可选，新旋转
    "scale": [2, 2, 2],  // 可选，新缩放
    "hide": false  // 可选，是否隐藏
}
```

**返回值**：

```json
{
    "name": "对象名称",
    "location": [1, 1, 1],
    "rotation": [0, 0, 0],
    "scale": [2, 2, 2],
    "hide": false
}
```

### blender.object.delete

删除对象。

**输入参数**：

```json
{
    "name": "对象名称"  // 要删除的对象名称
}
```

**返回值**：

```json
{
    "status": "ok",
    "message": "对象已删除"
}
```

### blender.material.create

创建新材质。

**输入参数**：

```json
{
    "name": "材质名称",  // 可选，材质名称
    "color": [1, 0, 0, 1],  // 可选，RGBA颜色
    "metallic": 0.0,  // 可选，金属度
    "roughness": 0.5,  // 可选，粗糙度
    "emission": [0, 0, 0, 1],  // 可选，发光颜色
    "emission_strength": 0.0  // 可选，发光强度
}
```

**返回值**：

```json
{
    "name": "材质名称",
    "color": [1, 0, 0, 1],
    "metallic": 0.0,
    "roughness": 0.5,
    "emission": [0, 0, 0, 1],
    "emission_strength": 0.0
}
```

### blender.material.assign

将材质分配给对象。

**输入参数**：

```json
{
    "object": "对象名称",  // 对象名称
    "material": "材质名称"  // 材质名称
}
```

**返回值**：

```json
{
    "object": "对象名称",
    "material": "材质名称",
    "status": "ok"
}
```

### blender.scene.render

渲染当前场景。

**输入参数**：

```json
{
    "resolution_x": 1920,  // 可选，水平分辨率
    "resolution_y": 1080,  // 可选，垂直分辨率
    "samples": 128,  // 可选，采样数
    "file_format": "PNG"  // 可选，输出格式
}
```

**返回值**：

```json
{
    "image": "base64编码的图像数据",
    "format": "PNG",
    "resolution": [1920, 1080]
}
```

### blender.code.execute

执行Blender Python代码。

**输入参数**：

```json
{
    "code": "import bpy\nbpy.ops.mesh.primitive_cube_add()"  // 要执行的Python代码
}
```

**返回值**：

```json
{
    "status": "ok",
    "result": "代码执行结果"
}
```

## WebSocket连接示例

以下是使用JavaScript通过WebSocket连接到BlenderMCP服务器的示例：

```javascript
// 创建WebSocket连接
const ws = new WebSocket('ws://localhost:9876');

// 连接打开时
ws.onopen = function() {
    console.log('连接已打开');
    
    // 发送初始化请求
    const initRequest = {
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {}
    };
    
    ws.send(JSON.stringify(initRequest));
};

// 接收消息
ws.onmessage = function(event) {
    const response = JSON.parse(event.data);
    console.log('收到响应:', response);
    
    // 处理响应
    if (response.result) {
        // 成功响应
        console.log('成功:', response.result);
    } else if (response.error) {
        // 错误响应
        console.error('错误:', response.error);
    }
};

// 连接关闭时
ws.onclose = function() {
    console.log('连接已关闭');
};

// 连接错误时
ws.onerror = function(error) {
    console.error('WebSocket错误:', error);
};

// 调用工具示例
function callTool(name, params) {
    const request = {
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'callTool',
        params: {
            name: name,
            params: params
        }
    };
    
    ws.send(JSON.stringify(request));
}

// 示例：创建立方体
callTool('blender.object.create', {
    type: 'cube',
    location: [0, 0, 0],
    size: 2.0
});

// 示例：渲染场景
callTool('blender.scene.render', {
    resolution_x: 1920,
    resolution_y: 1080
});

// 关闭连接
function closeConnection() {
    const request = {
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'shutdown',
        params: {}
    };
    
    ws.send(JSON.stringify(request));
}
```

## STDIO连接示例

以下是使用Python通过STDIO连接到BlenderMCP服务器的示例：

```python
import json
import sys
import struct

def send_message(message):
    """发送消息到STDIO服务器"""
    json_str = json.dumps(message)
    data = json_str.encode('utf-8')
    
    # 写入消息长度（4字节整数）
    sys.stdout.buffer.write(struct.pack('>I', len(data)))
    
    # 写入消息内容
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()

def receive_message():
    """从STDIO服务器接收消息"""
    # 读取消息长度（4字节整数）
    length_bytes = sys.stdin.buffer.read(4)
    length = struct.unpack('>I', length_bytes)[0]
    
    # 读取消息内容
    data = sys.stdin.buffer.read(length)
    json_str = data.decode('utf-8')
    
    return json.loads(json_str)

# 发送初始化请求
init_request = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {}
}

send_message(init_request)
init_response = receive_message()
print('初始化响应:', init_response)

# 调用工具示例
tool_request = {
    'jsonrpc': '2.0',
    'id': 2,
    'method': 'callTool',
    'params': {
        'name': 'blender.object.create',
        'params': {
            'type': 'cube',
            'location': [0, 0, 0]
        }
    }
}

send_message(tool_request)
tool_response = receive_message()
print('工具响应:', tool_response)

# 发送关闭请求
shutdown_request = {
    'jsonrpc': '2.0',
    'id': 3,
    'method': 'shutdown',
    'params': {}
}

send_message(shutdown_request)
shutdown_response = receive_message()
print('关闭响应:', shutdown_response)
```

## 注意事项

1. **错误处理** - 始终检查响应中是否存在错误字段，并适当处理错误
2. **异步通信** - WebSocket通信是异步的，确保正确处理响应
3. **资源管理** - 在完成操作后关闭连接，释放资源
4. **安全性** - 小心使用`blender.code.execute`工具，它可以执行任意Python代码 