# BlenderMCP 故障排除指南

## 事件循环问题

### 问题1: 事件循环嵌套

**错误信息**
```
ERROR: This event loop is already running
```

**原因分析**
1. 在 `run_in_blender` 函数中，我们试图在已经运行的事件循环中再次运行事件循环
2. 这种情况通常发生在以下场景：
   - WebSocket服务器已经在一个事件循环中运行
   - 然后我们尝试在处理请求时使用 `run_until_complete` 或类似方法启动另一个事件循环

**解决方案**
1. 使用线程本地存储来管理事件循环：
```python
import threading
import asyncio

# 线程本地存储
_thread_locals = threading.local()

def get_or_create_event_loop():
    """获取或创建事件循环"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

def run_in_blender(func: Callable) -> Any:
    """在Blender主线程中执行函数"""
    try:
        logger.debug("准备在Blender主线程中执行函数")
        
        # 创建Future对象
        if not hasattr(_thread_locals, 'loop'):
            _thread_locals.loop = get_or_create_event_loop()
        future = _thread_locals.loop.create_future()
        
        def timer_function():
            if future.done():
                logger.debug("Future已完成，跳过执行")
                return None
                
            try:
                logger.debug("开始在Blender主线程中执行函数")
                result = func()
                logger.debug(f"函数执行成功，结果: {result}")
                if not future.done():
                    future.set_result(result)
            except Exception as e:
                logger.error(f"在Blender主线程中执行函数时出错: {e}")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                if not future.done():
                    future.set_exception(e)
            return None
            
        # 注册定时器函数
        logger.debug("注册定时器函数")
        bpy.app.timers.register(timer_function, first_interval=0.0, persistent=True)
        
        # 等待结果
        try:
            logger.debug("等待执行结果")
            # 使用同步等待而不是事件循环
            result = future.result(timeout=5.0)
            logger.debug(f"获得执行结果: {result}")
            return result
        except asyncio.TimeoutError:
            logger.error("等待结果超时")
            raise BlenderError("操作超时")
        except Exception as e:
            logger.error(f"等待结果时出错: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise
        finally:
            # 清理定时器
            if bpy.app.timers.is_registered(timer_function):
                bpy.app.timers.unregister(timer_function)
                
    except Exception as e:
        logger.error(f"run_in_blender执行出错: {e}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise BlenderError(str(e))
```

2. 在服务器启动时保存事件循环引用：
```python
class BlenderMCPServer:
    def __init__(self, host: str = "localhost", port: int = 9876):
        self.host = host
        self.port = port
        self.server = None
        self._running = False
        self._command_handlers = {}
        self._startup_event = threading.Event()
        self._loop = None  # 保存事件循环引用
        
    async def start(self):
        if self._running:
            logger.warning("服务器已经在运行")
            return
            
        try:
            # 保存事件循环引用
            self._loop = asyncio.get_event_loop()
            
            # 启动服务器
            logger.info(f"启动服务器: {self.host}:{self.port}")
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            self._running = True
            self._startup_event.set()
            logger.info("服务器启动成功")
            
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            self._startup_event.set()  # 设置事件以避免阻塞
            raise
```

**注意事项**
1. 确保在不同线程中使用不同的事件循环
2. 避免在已运行的事件循环中使用 `run_until_complete`
3. 使用 `future.result()` 进行同步等待，而不是启动新的事件循环
4. 在服务器启动时保存事件循环引用，以便在其他地方使用

**相关文件**
- `src/blendermcp/server/handlers/blender_handler.py`
- `src/blendermcp/server/core.py`
- `src/blendermcp/server/server.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 运行测试脚本
5. 检查是否还有事件循环相关错误

**参考资料**
- [Python asyncio文档](https://docs.python.org/3/library/asyncio.html)
- [Blender Python API文档](https://docs.blender.org/api/current/)

### 问题2: run_until_complete 在已运行的事件循环中调用

**错误信息**
```
ERROR: This event loop is already running
```

**原因分析**
在 `run_in_blender` 函数中，我们使用 `loop.run_until_complete()` 来等待结果，但是当事件循环已经在运行时（例如在WebSocket服务器的事件循环中），这会导致错误。这是因为不能在一个正在运行的事件循环中调用 `run_until_complete`。

**解决方案**
使用 `asyncio.get_running_loop()` 和 `asyncio.create_task()` 来替代 `run_until_complete`：

```python
def run_in_blender(func: Callable) -> Any:
    """在Blender主线程中执行函数"""
    try:
        logger.debug("准备在Blender主线程中执行函数")
        
        # 获取当前运行的事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # 创建Future对象
        future = loop.create_future()
        
        def timer_function():
            if future.done():
                return None
                
            try:
                result = func()
                if not future.done():
                    loop.call_soon_threadsafe(future.set_result, result)
            except Exception as e:
                if not future.done():
                    loop.call_soon_threadsafe(future.set_exception, e)
            return None
            
        # 注册定时器函数
        bpy.app.timers.register(timer_function, first_interval=0.0, persistent=True)
        
        # 等待结果
        try:
            # 使用asyncio.wait_for而不是run_until_complete
            return asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            raise BlenderError("操作超时")
        finally:
            if bpy.app.timers.is_registered(timer_function):
                bpy.app.timers.unregister(timer_function)
                
    except Exception as e:
        raise BlenderError(str(e))
```

**注意事项**
1. 使用 `asyncio.get_running_loop()` 获取当前运行的事件循环
2. 使用 `loop.call_soon_threadsafe()` 在事件循环线程中安全地设置结果
3. 返回 coroutine 而不是直接等待结果，让调用者决定如何等待
4. 确保在定时器函数中使用线程安全的方式设置结果

**相关文件**
- `src/blendermcp/server/handlers/blender_handler.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 运行测试脚本
5. 检查是否还有事件循环相关错误

**参考资料**
- [Python asyncio文档](https://docs.python.org/3/library/asyncio.html) 

### 问题3: 材质设置参数不匹配

**错误信息**
```
ERROR: Object name is required
```

**原因分析**
在 `set_material` 方法中，参数名称的处理存在问题。该方法需要支持两种不同的参数名称格式：
1. `object` - 在新版本中使用
2. `object_name` - 为了向后兼容

使用 `or` 运算符来检查这两个参数可能会导致问题，特别是当 `object` 参数存在但值为空字符串或 `False` 时。

**解决方案**
修改 `set_material` 方法中的参数处理逻辑，使用更严格的检查：

```python
@staticmethod
async def set_material(params: Dict[str, Any]) -> Dict[str, Any]:
    """Set material for an object"""
    try:
        logger.info(f"开始设置材质，参数: {params}")
        # 支持两种参数名称格式
        obj_name = params.get('object')
        if obj_name is None:
            obj_name = params.get('object_name')
        if not obj_name:
            raise ParameterError("Object name is required")
            
        material_name = params.get('material')
        color = params.get('color', (0.8, 0.8, 0.8, 1.0))
        
        def set_material_sync():
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                raise BlenderError(f"Object not found: {obj_name}")
                
            # 创建或获取材质
            mat = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    mat = bpy.data.materials.new(name=material_name)
            else:
                mat = bpy.data.materials.new(name=f"{obj_name}_material")
                
            # 设置材质属性
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = color
                
            # 应用材质到对象
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
                
            return {
                'object': obj_name,
                'material': mat.name,
                'color': tuple(color)
            }
            
        return await run_in_blender(set_material_sync)
        
    except Exception as e:
        logger.exception("Error setting material")
        raise BlenderError(str(e))
```

**注意事项**
1. 使用 `is None` 检查来确保正确处理所有有效值
2. 分别检查每个参数名称
3. 保持清晰的错误消息
4. 确保参数名称的兼容性

**相关文件**
- `src/blendermcp/server/handlers/blender_handler.py`
- `tests/test_basic_operations.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 运行测试脚本
5. 验证材质是否正确应用到对象上

**参考资料**
- [Python 字典操作](https://docs.python.org/3/library/stdtypes.html#dict)
- [Blender Python API - Materials](https://docs.blender.org/api/current/bpy.types.Material.html) 

### 问题4: 客户端和服务器端参数名称不匹配

**错误信息**
```
ERROR: Object name is required
```

**原因分析**
在客户端和服务器端之间存在参数名称不匹配的问题：
1. 客户端代码中使用了 `PARAM_NAME` 和 `PARAM_MATERIAL_NAME` 作为参数名
2. 服务器端代码期望 `object` 和 `material` 作为参数名
3. 测试代码中使用了 `object_name` 和 `material_name` 作为参数名

这种不一致导致服务器无法正确识别参数。

**解决方案**
修改客户端代码中的 `set_material` 方法，使用正确的参数名称：

```python
async def set_material(
    self,
    object_name: str,
    material_name: Optional[str] = None,
    color: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Set or create a material for an object"""
    logger.info(f"设置材质: object={object_name}, material={material_name}")
    params = {"object": object_name}  # 使用 "object" 而不是 PARAM_NAME
    if material_name:
        params["material"] = material_name  # 使用 "material" 而不是 PARAM_MATERIAL_NAME
    if color:
        params[PARAM_COLOR] = color
    return await self.send_command(SET_MATERIAL, params)
```

**注意事项**
1. 确保客户端和服务器端使用相同的参数名称
2. 在协议定义中明确指定参数名称
3. 保持参数名称的一致性
4. 在文档中清晰说明参数名称的要求

**相关文件**
- `src/blendermcp/client/client.py`
- `src/blendermcp/client/protocol/commands.py`
- `src/blendermcp/server/handlers/blender_handler.py`
- `tests/test_basic_operations.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 运行测试脚本
5. 验证材质是否正确应用到对象上

**参考资料**
- [Python 字典操作](https://docs.python.org/3/library/stdtypes.html#dict)
- [Blender Python API - Materials](https://docs.blender.org/api/current/bpy.types.Material.html) 

### 问题5: 材质设置中的变量作用域问题

**错误信息**
```
ERROR: cannot access local variable 'color' where it is not associated with a value
```

**原因分析**
在 `set_material` 方法中，内部函数 `set_material_sync` 试图访问外部作用域中的 `color` 变量，但由于 Python 的变量作用域规则，这个变量在内部函数中无法访问。这是因为：
1. 内部函数创建了自己的作用域
2. 外部变量在内部函数中被引用时需要特别处理
3. 变量名重用可能导致作用域混淆

**解决方案**
修改变量名以避免作用域冲突，并确保内部函数可以访问所有需要的变量：

```python
@staticmethod
async def set_material(params: Dict[str, Any]) -> Dict[str, Any]:
    """Set material for an object"""
    try:
        logger.info(f"开始设置材质，参数: {params}")
        # 支持两种参数名称格式
        obj_name = params.get('object')
        if obj_name is None:
            obj_name = params.get('object_name')
        if not obj_name:
            raise ParameterError("Object name is required")
            
        material_name = params.get('material')
        color_value = params.get('color', (0.8, 0.8, 0.8, 1.0))  # 使用不同的变量名
        
        def set_material_sync():
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                raise BlenderError(f"Object not found: {obj_name}")
                
            # 创建或获取材质
            mat = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    mat = bpy.data.materials.new(name=material_name)
            else:
                mat = bpy.data.materials.new(name=f"{obj_name}_material")
                
            # 设置材质属性
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs['Base Color'].default_value = color_value
                
            # 应用材质到对象
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
                
            return {
                'object': obj_name,
                'material': mat.name,
                'color': tuple(color_value)
            }
            
        return await run_in_blender(set_material_sync)
        
    except Exception as e:
        logger.exception("Error setting material")
        raise BlenderError(str(e))
```

**注意事项**
1. 使用不同的变量名避免作用域冲突
2. 确保内部函数可以访问所有需要的外部变量
3. 注意 Python 的变量作用域规则
4. 在嵌套函数中小心使用同名变量

**相关文件**
- `src/blendermcp/server/handlers/blender_handler.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 运行测试脚本
5. 验证材质是否正确应用到对象上

**参考资料**
- [Python 作用域规则](https://docs.python.org/3/tutorial/classes.html#python-scopes-and-namespaces)
- [Python 闭包](https://docs.python.org/3/reference/execution.html#naming-and-binding) 

### 问题6: set_material方法参数名称错误

**错误信息**
```
TypeError: BlenderMCPClient.set_material() got an unexpected keyword argument 'object'
```

**原因分析**
在 `demos/chess_set.py` 中，我们使用了 `object` 作为 `set_material` 方法的参数名，但是根据客户端API的定义，应该使用 `object_name`。这是因为：
1. `BlenderMCPClient.set_material()` 方法定义使用了 `object_name` 作为参数名
2. 服务器端代码支持 `object` 和 `object_name`，但客户端API只支持 `object_name`
3. 这种不一致导致了类型错误

**解决方案**
修改 `demos/chess_set.py` 中的 `set_material` 方法，使用正确的参数名称：

```python
async def set_material(
    self,
    object_name: str,
    material_name: Optional[str] = None,
    color: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Set or create a material for an object"""
    logger.info(f"设置材质: object={object_name}, material={material_name}")
    params = {"object": object_name}  # 使用 "object" 而不是 PARAM_NAME
    if material_name:
        params["material"] = material_name  # 使用 "material" 而不是 PARAM_MATERIAL_NAME
    if color:
        params[PARAM_COLOR] = color
    return await self.send_command(SET_MATERIAL, params)
```

**注意事项**
1. 确保使用正确的参数名称：`object_name` 而不是 `object`
2. 同样，使用 `material_name` 而不是 `material`
3. 检查API文档以确保使用正确的参数名称
4. 在整个代码中保持参数名称的一致性

**相关文件**
- `demos/chess_set.py`
- `src/blendermcp/client/client.py`
- `src/blendermcp/server/handlers/blender_handler.py`

**测试步骤**
1. 修改所有 `set_material` 调用中的参数名称
2. 重启 Blender
3. 启用插件
4. 启动服务器
5. 运行测试脚本
6. 验证材质是否正确应用到对象上

**参考资料**
- [Python 字典操作](https://docs.python.org/3/library/stdtypes.html#dict)
- [BlenderMCP API文档]() 

### 问题7: set_material方法不支持高级材质参数

**错误信息**
```
TypeError: BlenderMCPClient.set_material() got an unexpected keyword argument 'metallic'
```

**原因分析**
在 `demos/chess_set.py` 中，我们尝试为材质设置高级属性（metallic、roughness、specular），但是客户端的 `set_material` 方法只支持基本参数：
1. `BlenderMCPClient.set_material()` 方法只接受 `object_name`、`material_name` 和 `color` 参数
2. 服务器端支持更多材质属性，但客户端API没有暴露这些参数
3. 需要修改客户端API以支持这些高级材质属性

**解决方案**
有两种解决方案：

1. 修改客户端代码中的 `set_material` 方法，添加对高级材质属性的支持：

```python
async def set_material(
    self,
    object_name: str,
    material_name: Optional[str] = None,
    color: Optional[List[float]] = None,
    metallic: Optional[float] = None,
    roughness: Optional[float] = None,
    specular: Optional[float] = None
) -> Dict[str, Any]:
    """Set or create a material for an object with advanced properties"""
    logger.info(f"设置材质: object={object_name}, material={material_name}")
    params = {
        "object": object_name,
        "material": material_name
    }
    if color is not None:
        params["color"] = color
    if metallic is not None:
        params["metallic"] = metallic
    if roughness is not None:
        params["roughness"] = roughness
    if specular is not None:
        params["specular"] = specular
    return await self.send_command("set_material", params)
```

2. 或者修改 `demos/chess_set.py` 中的材质设置代码，只使用基本参数：

```python
# 修改前
material_params = {
    "object_name": piece["name"],
    "material_name": material_name,
    "color": color,
    "metallic": 0.0 if is_white else 0.1,
    "roughness": 0.3 if is_white else 0.4,
    "specular": 0.7 if is_white else 0.5
}
await client.set_material(**material_params)

# 修改后
await client.set_material(
    object_name=piece["name"],
    material_name=material_name,
    color=color
)
```

**注意事项**
1. 确保客户端API文档清晰说明支持的参数
2. 在添加新参数时保持向后兼容性
3. 考虑使用材质节点系统来设置高级属性
4. 在服务器端正确处理这些高级属性

**相关文件**
- `demos/chess_set.py`
- `src/blendermcp/client/client.py`
- `src/blendermcp/server/handlers/blender_handler.py`

**测试步骤**
1. 选择一个解决方案实施
2. 修改相关代码
3. 重启 Blender
4. 启用插件
5. 启动服务器
6. 运行测试脚本
7. 验证材质是否正确应用，包括基本和高级属性

**参考资料**
- [Blender Python API - Materials](https://docs.blender.org/api/current/bpy.types.Material.html)
- [Blender材质节点系统文档](https://docs.blender.org/manual/en/latest/render/shader_nodes/index.html) 

### 问题8: 服务器启动时的导入循环依赖问题

**错误信息**
```
服务器启动失败: Traceback (most recent call last):
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\server\run_mcp_server.py", line 28, in <module>
    from blendermcp.tools import register_all_tools
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\__init__.py", line 30, in <module>
    from .addon import register, unregister
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\addon\__init__.py", line 32, in <module>
    from . import server_operators
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\addon\server_operators.py", line 433, in <module>
    class MCP_OT_StartServer(Operator):
                             ^^^^^^^^
NameError: name 'Operator' is not defined
```

**原因分析**
1. 导入链形成了循环依赖：
   - 服务器 `run_mcp_server.py` 导入 `blendermcp.tools` 模块
   - 这触发了导入整个 `blendermcp` 包
   - 导入过程继续到 `blendermcp.addon` 模块
   - 然后导入 `server_operators.py` 模块
2. `server_operators.py` 中尝试使用 try-except 来处理 `bpy` 的导入：
   ```python
   try:
       import bpy
       from bpy.types import Operator
   except ImportError:
       pass  # 在没有bpy模块时不会报错
   ```
3. 虽然使用了 try-except 块，但是当导入失败时，代码没有为 `Operator` 提供替代定义
4. 因此，在后续的类定义中使用 `Operator` 时，发生了 `NameError`

**解决方案**
1. 在 `server_operators.py` 中，为 `Operator` 提供替代定义：
```python
try:
    import bpy
    from bpy.types import Operator
except ImportError:
    # 在没有bpy模块时创建一个空的Operator类作为替代
    class Operator:
        """替代Blender的Operator类，用于服务器独立运行时"""
        bl_idname = ""
        bl_label = ""
        bl_description = ""
        
        def execute(self, context):
            return {'FINISHED'}
        
        def report(self, type, message):
            print(f"Report [{type}]: {message}")
```

2. 修改 `run_mcp_server.py` 的导入方式，避免导入整个 `blendermcp` 包：
```python
# 直接导入需要的函数，避免导入整个blendermcp包
# from blendermcp.tools import register_all_tools
# 修改为直接导入，避免导入循环
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from tools import register_all_tools
except ImportError:
    # 尝试相对导入
    try:
        from .tools import register_all_tools
    except ImportError:
        # 如果都失败，尝试绝对导入
        from blendermcp.tools import register_all_tools
```

3. 增强 `write_tools_list` 函数和 `MCPAdapter` 类的错误处理能力，确保服务器可以在各种情况下正常启动

**注意事项**
1. 避免导入循环依赖，尤其是在不同组件之间
2. 在 try-except 块中处理导入错误时，要为可能使用的名称提供替代定义
3. 使用更直接的导入方式，避免导入整个包
4. 增强关键函数的错误处理能力，确保程序在各种情况下都能正常运行
5. 使用适当的日志记录，帮助诊断问题

**相关文件**
- `src/blendermcp/server/run_mcp_server.py`
- `src/blendermcp/addon/server_operators.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 确认服务器能够正常启动并运行
5. 检查日志文件，确保没有严重错误

**参考资料**
- [Python 导入系统](https://docs.python.org/3/reference/import.html)
- [处理循环导入](https://docs.python.org/3/faq/programming.html#what-are-the-best-practices-for-using-import-in-a-module) 

### 问题9: 服务器启动模式大小写不匹配

**错误信息**
```
服务器启动失败: usage: run_mcp_server.py [-h] [--mode {websocket,stdio}] [--host HOST]
                      [--port PORT]
run_mcp_server.py: error: argument --mode: invalid choice: 'WEBSOCKET' (choose from 'websocket', 'stdio')
```

**原因分析**
1. 在启动MCP服务器时，传递了大写的模式参数`--mode WEBSOCKET`
2. 但`run_mcp_server.py`脚本只接受小写的选项："websocket"或"stdio"
3. 在`server_operators.py`中，从Blender插件首选项获取的服务器模式是大写的（例如'WEBSOCKET'），但在构建命令行参数时，需要使用小写

**解决方案**
修改`server_operators.py`中的启动代码，将服务器模式转换为小写：

```python
# 启动独立进程
cmd = [
    python_exe,
    server_script,
    "--mode", server_mode.lower(),  # 将模式转换为小写
    "--host", server_host,
    "--port", server_port
]
```

**注意事项**
1. 命令行参数通常对大小写敏感
2. 当涉及到从一个系统（如Blender的枚举属性）到另一个系统（如命令行参数）的值传递时，需要注意可能的格式差异
3. 在构建命令行参数时，最好进行适当的格式转换和验证

**相关文件**
- `src/blendermcp/addon/server_operators.py`
- `src/blendermcp/server/run_mcp_server.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 确认服务器能够正常启动
5. 检查日志文件，确保没有相关错误

**参考资料**
- [Python argparse文档](https://docs.python.org/3/library/argparse.html)
- [字符串处理方法](https://docs.python.org/3/library/stdtypes.html#string-methods) 

### 问题10: 运行服务器时的asyncio模块导入中断问题

**错误信息**
```
服务器启动失败: Traceback (most recent call last):
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\server\run_mcp_server.py", line 605, in <module>
    asyncio.run(main())
  // ... 中间堆栈 ...
  File "C:\Users\kangdong\AppData\Roaming\Python\Python311\site-packages\websockets\asyncio\server.py", line 3, in <module>
    import asyncio
ModuleNotFoundError: import of asyncio halted; None in sys.modules
```

**原因分析**
1. 这个错误表明在导入`asyncio`模块时发生了中断，提示`None in sys.modules`
2. 这种情况通常是由于Python导入机制中的复杂交互导致的：
   - 导入过程中，Python会先在`sys.modules`中将模块标记为`None`
   - 如果导入过程被中断（例如由于循环导入或其他错误），模块可能保持为`None`状态
   - 后续对该模块的导入会失败，因为Python认为它已经在导入中（但实际上是失败的）
3. 在我们的代码中，问题的原因可能是：
   - 模拟`bpy`模块的方式干扰了Python的导入机制
   - 修改`sys.path`的时机或方式不当
   - 模块导入顺序有问题
   - 循环导入问题

**解决方案**
1. 确保`asyncio`在任何可能干扰导入的代码之前被导入：
```python
# 文件顶部首先导入标准库模块，尤其是asyncio
import os
import sys
import asyncio  # 确保asyncio最先导入
import json
import time
import argparse
import tempfile
import logging
# ... 其他导入
```

2. 改进模拟`bpy`模块的方式，避免干扰已存在的模块：
```python
# 安全地创建模拟的bpy模块，确保不干扰已存在的模块
if 'bpy' not in sys.modules:
    try:
        logger.info("创建模拟的bpy模块")
        
        class MockBpy:
            # 模拟bpy模块的基本结构
            # ... 类定义
        
        sys.modules['bpy'] = MockBpy()
        logger.info("成功创建模拟的bpy模块")
    except Exception as e:
        logger.error(f"创建模拟的bpy模块时出错: {str(e)}")
```

3. 改进事件循环的创建和管理：
```python
if __name__ == "__main__":
    # 确保清理任何可能存在的事件循环
    if hasattr(asyncio, '_get_running_loop'):
        if asyncio._get_running_loop() is not None:
            logger.warning("检测到已有事件循环在运行，将创建新的事件循环")
    
    try:
        # 为Windows平台设置正确的事件循环策略
        if sys.platform == 'win32':
            logger.info("为Windows设置事件循环策略")
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # 确保使用新的事件循环
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("已设置新的事件循环")
        except Exception as e:
            logger.error(f"设置事件循环时出错: {str(e)}")
            raise
        
        # 使用asyncio.run运行主函数
        logger.info("开始运行主函数")
        asyncio.run(main())
    except Exception as e:
        # 错误处理
```

4. 增强错误处理和日志记录，确保能捕获并报告错误：
```python
async def websocket_server(host, port):
    """启动WebSocket服务器"""
    try:
        # ... 代码
        try:
            # 这里是可能出现asyncio导入错误的地方
            logger.debug("尝试创建WebSocket服务器")
            server = await websockets.serve(handle_connection, host, port)
            # ... 成功处理
        except Exception as e:
            logger.error(f"启动WebSocket服务器失败: {str(e)}")
            import traceback
            logger.error(f"WebSocket服务器启动错误堆栈: {traceback.format_exc()}")
            raise
    except Exception as e:
        logger.error(f"WebSocket服务器函数执行失败: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise
```

**注意事项**
1. 在Python中处理模块导入需要格外小心，尤其是当涉及到`asyncio`这样的核心模块时
2. 导入顺序很重要：先导入标准库模块，然后是第三方模块，最后是自定义模块
3. 避免不必要地修改`sys.modules`或`sys.path`，尤其是在导入过程中
4. 模拟内置模块（如`bpy`）时，确保不干扰其他模块的导入
5. 使用详细的日志记录，帮助诊断导入问题
6. 为关键代码区域添加详细的错误处理，捕获并报告异常

**相关文件**
- `src/blendermcp/server/run_mcp_server.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 确认服务器能够正常启动并运行
5. 检查日志文件，确保没有相关错误

**参考资料**
- [Python 导入系统](https://docs.python.org/3/reference/import.html)
- [asyncio 文档](https://docs.python.org/3/library/asyncio.html)
- [sys.modules 文档](https://docs.python.org/3/library/sys.html#sys.modules)
- [Python异步编程指南](https://docs.python.org/3/library/asyncio-task.html)

### 问题11: 面板定义缺少Panel类替代

**错误信息**
```
服务器启动失败: Traceback (most recent call last):
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\server\run_mcp_server.py", line 55, in <module>
    from blendermcp.tools import register_all_tools
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\__init__.py", line 30, in <module>
    from .addon import register, unregister
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\addon\__init__.py", line 34, in <module>
    from . import panels
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\addon\panels.py", line 18, in <module>
    class MCP_PT_Panel(Panel):
                       ^^^^^
NameError: name 'Panel' is not defined
```

**原因分析**
1. 这个问题是我们之前修复的问题8（导入循环依赖）的延续
2. 当服务器启动时，导入链仍然会导入整个`blendermcp`包，然后导入`addon`模块和其子模块
3. 在`panels.py`模块中，如果`bpy`导入失败，`Panel`类未被定义
4. 类似于之前在`server_operators.py`中解决的问题，我们需要为`Panel`类提供替代定义

**解决方案**
在`panels.py`文件中，为`Panel`类提供替代定义：

```python
try:
    import bpy
    from bpy.types import Panel
except ImportError:
    # 在没有bpy模块时创建一个空的Panel类作为替代
    class Panel:
        """替代Blender的Panel类，用于服务器独立运行时"""
        bl_idname = ""
        bl_label = ""
        bl_description = ""
        bl_space_type = "PROPERTIES"
        bl_region_type = "WINDOW"
        bl_context = "scene"
        
        def draw(self, context):
            pass
```

**注意事项**
1. 当开发Blender插件并同时希望能够独立运行服务器时，需要为所有Blender特定的类提供替代定义
2. 除了`Operator`和`Panel`之外，可能还需要为其他Blender类提供替代定义，如`PropertyGroup`、`Menu`等
3. 替代定义应该包含足够的属性和方法，以便代码在没有Blender环境时仍能正常运行
4. 确保在导入循环链上的每个文件中都正确处理导入错误

**相关文件**
- `src/blendermcp/addon/panels.py`
- `src/blendermcp/addon/server_operators.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 确认服务器能够正常启动并运行
5. 检查日志文件，确保没有相关错误

**参考资料**
- [Python 导入系统](https://docs.python.org/3/reference/import.html)
- [Blender API - Panel类](https://docs.blender.org/api/current/bpy.types.Panel.html)

### 问题12: Blender特有类的替代方案总结

**问题概述**
在BlenderMCP开发中，我们面临一个常见挑战：同一套代码需要在两种不同的环境中运行：
1. 在Blender内部作为插件运行
2. 在Blender外部作为独立服务器运行

这导致了多个与Blender特有类相关的导入错误，例如`Panel`、`Operator`、`PropertyGroup`等。

**通用解决方案**
为了解决此类问题，我们采用以下通用模式：

```python
try:
    import bpy
    from bpy.types import Panel, Operator, PropertyGroup  # 等等
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    
    # 提供替代类定义
    class Panel:
        """替代Blender的Panel类，用于服务器独立运行时"""
        bl_idname = ""
        bl_label = ""
        # ... 添加必要的属性 ...
        
        def draw(self, context):
            pass
    
    class Operator:
        """替代Blender的Operator类，用于服务器独立运行时"""
        bl_idname = ""
        bl_label = ""
        # ... 添加必要的属性 ...
        
        def execute(self, context):
            return {'FINISHED'}
    
    # 其他Blender特有类的替代定义
    # ...
```

**我们已经修改的文件**
- `src/blendermcp/addon/panels.py` - 提供`Panel`类替代
- `src/blendermcp/addon/server_operators.py` - 提供`Operator`类替代
- `src/blendermcp/addon/properties.py` - 提供`PropertyGroup`类和属性函数替代
- `src/blendermcp/addon/tool_viewer.py` - 提供全面的UI相关类替代
- `src/blendermcp/addon/preferences.py` - 提供`AddonPreferences`类替代

**未来可能需要修改的文件**
如果遇到类似的导入错误，请检查以下文件类型：
- Blender面板定义文件
- Blender操作符定义文件
- Blender属性定义文件
- 任何导入和使用bpy模块的文件

**最佳实践**
1. 始终使用`try/except`包装Blender特有的导入
2. 提供足够完整的替代类定义，包含必要的属性和方法
3. 使用条件判断（如`if HAS_BPY:`）来区分不同环境的行为
4. 确保替代类提供与原始类相同的接口
5. 在文档中记录此类修改，以便其他开发者理解代码结构

通过遵循这些实践，可以确保BlenderMCP代码在不同环境中都能正常运行，实现代码的复用和一致性。

### 问题13: asyncio模块导入中断问题

**错误信息**
```
服务器启动失败: Traceback (most recent call last):
  File "C:\Users\kangdong\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blendermcp\server\run_mcp_server.py", line 605, in <module>
    asyncio.run(main())
  // ... 中间堆栈 ...
  File "C:\Users\kangdong\AppData\Roaming\Python\Python311\site-packages\websockets\asyncio\server.py", line 3, in <module>
    import asyncio
ModuleNotFoundError: import of asyncio halted; None in sys.modules
```

**原因分析**
1. 这个错误表明在导入`asyncio`模块时发生了中断，提示`None in sys.modules`
2. 这种情况通常是由于Python导入机制中的复杂交互导致的：
   - 导入过程中，Python会先在`sys.modules`中将模块标记为`None`
   - 如果导入过程被中断（例如由于循环导入或其他错误），模块可能保持为`None`状态
   - 后续对该模块的导入会失败，因为Python认为它已经在导入中（但实际上是失败的）
3. 在我们的代码中，问题的原因可能是：
   - 模拟`bpy`模块的方式干扰了Python的导入机制
   - 修改`sys.path`的时机或方式不当
   - 模块导入顺序有问题
   - 循环导入问题

**解决方案**
1. 确保`asyncio`在任何可能干扰导入的代码之前被导入：
```python
# 文件顶部首先导入标准库模块，尤其是asyncio
import os
import sys
import asyncio  # 确保asyncio最先导入
import json
import time
import argparse
import tempfile
import logging
# ... 其他导入
```

2. 改进模拟`bpy`模块的方式，避免干扰已存在的模块：
```python
# 安全地创建模拟的bpy模块，确保不干扰已存在的模块
if 'bpy' not in sys.modules:
    try:
        logger.info("创建模拟的bpy模块")
        
        class MockBpy:
            # 模拟bpy模块的基本结构
            # ... 类定义
        
        sys.modules['bpy'] = MockBpy()
        logger.info("成功创建模拟的bpy模块")
    except Exception as e:
        logger.error(f"创建模拟的bpy模块时出错: {str(e)}")
```

3. 改进事件循环的创建和管理：
```python
if __name__ == "__main__":
    # 确保清理任何可能存在的事件循环
    if hasattr(asyncio, '_get_running_loop'):
        if asyncio._get_running_loop() is not None:
            logger.warning("检测到已有事件循环在运行，将创建新的事件循环")
    
    try:
        # 为Windows平台设置正确的事件循环策略
        if sys.platform == 'win32':
            logger.info("为Windows设置事件循环策略")
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # 确保使用新的事件循环
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("已设置新的事件循环")
        except Exception as e:
            logger.error(f"设置事件循环时出错: {str(e)}")
            raise
        
        # 使用asyncio.run运行主函数
        logger.info("开始运行主函数")
        asyncio.run(main())
    except Exception as e:
        # 错误处理
```

4. 增强错误处理和日志记录，确保能捕获并报告错误：
```python
async def websocket_server(host, port):
    """启动WebSocket服务器"""
    try:
        # ... 代码
        try:
            # 这里是可能出现asyncio导入错误的地方
            logger.debug("尝试创建WebSocket服务器")
            server = await websockets.serve(handle_connection, host, port)
            # ... 成功处理
        except Exception as e:
            logger.error(f"启动WebSocket服务器失败: {str(e)}")
            import traceback
            logger.error(f"WebSocket服务器启动错误堆栈: {traceback.format_exc()}")
            raise
    except Exception as e:
        logger.error(f"WebSocket服务器函数执行失败: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise
```

**注意事项**
1. 在Python中处理模块导入需要格外小心，尤其是当涉及到`asyncio`这样的核心模块时
2. 导入顺序很重要：先导入标准库模块，然后是第三方模块，最后是自定义模块
3. 避免不必要地修改`sys.modules`或`sys.path`，尤其是在导入过程中
4. 模拟内置模块（如`bpy`）时，确保不干扰其他模块的导入
5. 使用详细的日志记录，帮助诊断导入问题
6. 为关键代码区域添加详细的错误处理，捕获并报告异常

**相关文件**
- `src/blendermcp/server/run_mcp_server.py`

**测试步骤**
1. 重启 Blender
2. 启用插件
3. 启动服务器
4. 确认服务器能够正常启动并运行
5. 检查日志文件，确保没有相关错误

**参考资料**
- [Python 导入系统](https://docs.python.org/3/reference/import.html)
- [asyncio 文档](https://docs.python.org/3/library/asyncio.html)
- [sys.modules 文档](https://docs.python.org/3/library/sys.html#sys.modules)
- [Python异步编程指南](https://docs.python.org/3/library/asyncio-task.html)

### 问题14: 没有找到工具和WebSocket连接问题

**错误信息**
```
没有找到工具 
ws客户端无法连接到服务器
```

**原因分析**
1. 工具查找问题可能有几个原因：
   - 工具注册函数未正确执行
   - 工具列表文件未被写入或访问权限问题
   - `register_all_tools`函数在执行时出现错误
   - `adapter.register_tool`方法使用不当

2. WebSocket连接问题可能由以下原因导致：
   - 服务器绑定在localhost而非0.0.0.0，只允许本地连接
   - 防火墙或网络设置阻止了连接
   - WebSocket服务器配置问题，如缺少`origins=None`设置
   - 端口可能被占用或被防火墙阻止

**解决方案**
1. 解决工具注册问题：
   - 添加测试工具确保基本工具可用：
   ```python
   def register_test_tool(adapter):
       """注册测试工具"""
       logger.info("注册测试工具")
       
       async def test_echo(params):
           """回显输入参数"""
           logger.info(f"测试工具被调用: {params}")
           return {"echo": params}
       
       adapter.register_tool(
           "blender.test.echo", 
           test_echo,
           "回显输入参数",
           [{"name": "message", "type": "string", "description": "要回显的消息"}]
       )
       logger.info("测试工具注册完成")
   ```

   - 修改Adapter类的register_tool方法：
   ```python
   def register_tool(self, name, handler, description=None, parameters=None):
       """注册工具"""
       logger.info(f"注册工具: {name}")
       self.tools[name] = {
           "handler": handler,
           "description": description or (handler.__doc__ or "").strip(),
           "parameters": parameters or []
       }
       logger.debug(f"工具 {name} 注册成功，描述: {description}，参数: {parameters}")
   ```

   - 完善工具调用处理：
   ```python
   async def _handle_tool_invocation(self, request_id, params):
       try:
           # ... 现有代码 ...
           
           # 获取工具处理函数
           tool = self.tools[tool_name]
           
           # 可能是直接函数或字典中的handler
           handler = tool if callable(tool) else tool.get("handler")
           
           if not callable(handler):
               logger.error(f"工具处理函数不可调用: {tool_name}")
               return self._create_error_response(request_id, -32603, f"工具处理函数不可调用: {tool_name}")
           
           # ... 现有代码 ...
       except Exception as e:
           # ... 错误处理 ...
   ```

2. 解决WebSocket连接问题：
   - 修改WebSocket服务器配置，使用`0.0.0.0`作为监听地址，允许来自任何接口的连接：
   ```python
   server_host = '0.0.0.0' if server_mode == 'WEBSOCKET' else 'localhost'
   ```
   
   - 确保asyncio正确导入，避免被模拟模块干扰：
   ```python
   import asyncio  # 确保asyncio在最前面导入
   # 其他导入...

   # 保存原始sys.modules状态，避免干扰已存在的模块
   original_modules = dict(sys.modules)

   # 再进行其他模块的模拟和导入
   ```

   - 检查服务器是否正在运行：
   ```powershell
   # Windows
   netstat -ano | findstr :9876
   ```

   - 检查服务器日志：
   ```powershell
   type $env:TEMP\blendermcp_server.log
   ```

### 问题15: WebSocket连接被拒绝

**错误信息**
```
测试连接到: ws://localhost:9876
连接失败: [WinError 1225] 远程计算机拒绝网络连接。
连接测试失败，退出
```

**原因分析**
1. 服务器没有正确启动或者没有监听正确的网络接口
2. 服务器可能仅监听localhost接口，无法从外部访问
3. asyncio导入问题导致WebSocket服务器启动失败
4. 端口可能被占用或被防火墙阻止

**解决方案**
1. 修改服务器配置，使用`0.0.0.0`作为监听地址，允许来自任何接口的连接：
```python
server_host = '0.0.0.0' if server_mode == 'WEBSOCKET' else 'localhost'
```

2. 确保asyncio正确导入，避免被模拟模块干扰：
```python
import asyncio  # 确保asyncio在最前面导入
# 其他导入...

# 保存原始sys.modules状态，避免干扰已存在的模块
original_modules = dict(sys.modules)

# 再进行其他模块的模拟和导入
```

3. 检查服务器是否正在运行：
```powershell
# Windows
netstat -ano | findstr :9876
```

4. 检查服务器日志：
```powershell
type $env:TEMP\blendermcp_server.log
```

### 问题16: 工具注册不完整

**错误信息**
```
工具列表文件存在，包含 1 个工具
```

**原因分析**
1. 工具注册过程可能出现错误
2. 模拟的bpy模块可能缺少某些必要的功能
3. 可能存在导入问题，导致只有默认工具被注册

**解决方案**
1. 添加测试工具函数，确保至少有一个基础工具可用：
```python
def register_test_tool(adapter):
    """注册测试工具"""
    logger.info("注册测试工具")
    
    async def test_echo(params):
        """回显输入参数"""
        logger.info(f"测试工具被调用: {params}")
        return {"echo": params}
    
    adapter.register_tool(
        "blender.test.echo", 
        test_echo,
        "回显输入参数",
        [{"name": "message", "type": "string", "description": "要回显的消息"}]
    )
```

2. 修改工具注册函数，优先注册测试工具，再尝试注册其他工具：
```python
def register_all_tools(adapter):
    # 先注册测试工具
    register_test_tool(adapter)
    
    try:
        # 尝试注册其他工具...
    except Exception as e:
        logger.error(f"注册工具时出错: {str(e)}")
        logger.info("只有测试工具被注册")
```

3. 确保工具列表写入函数能够在任何情况下写入可用的工具：
```python
# 在write_tools_list函数中
# 如果构建工具列表失败，确保至少有测试工具可用
if not tools_list:
    tools_list = [
        {
            "name": "blender.test.echo",
            "description": "回显输入参数",
            "parameters": [
                {"name": "message", "type": "string", "description": "要回显的消息"}
            ]
        }
    ]
```