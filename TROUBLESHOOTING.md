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