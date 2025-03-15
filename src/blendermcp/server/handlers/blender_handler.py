"""
BlenderMCP Blender Command Handlers

This module implements handlers for Blender-related commands.
"""

import bpy
import asyncio
import logging
import functools
import traceback
import threading
from typing import Dict, Any, Optional, Callable, Awaitable, Union, Coroutine
from ...common.errors import BlenderError, ParameterError

logger = logging.getLogger(__name__)

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

def run_in_blender(func: Callable) -> Coroutine[Any, Any, Any]:
    """在Blender主线程中执行函数"""
    async def wrapper():
        try:
            logger.debug("准备在Blender主线程中执行函数")
            
            # 获取当前运行的事件循环
            loop = asyncio.get_running_loop()
            
            # 创建Future对象
            future = loop.create_future()
            
            def timer_function():
                if future.done():
                    return None
                    
                try:
                    logger.debug("开始在Blender主线程中执行函数")
                    result = func()
                    logger.debug(f"函数执行成功，结果: {result}")
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_result, result)
                except Exception as e:
                    logger.error(f"在Blender主线程中执行函数时出错: {e}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_exception, e)
                return None
                
            # 注册定时器函数
            logger.debug("注册定时器函数")
            bpy.app.timers.register(timer_function, first_interval=0.0, persistent=True)
            
            try:
                # 等待结果，使用timeout避免无限等待
                return await asyncio.wait_for(future, timeout=5.0)
            finally:
                # 清理定时器
                if bpy.app.timers.is_registered(timer_function):
                    bpy.app.timers.unregister(timer_function)
                    
        except asyncio.TimeoutError:
            logger.error("等待结果超时")
            raise BlenderError("操作超时")
        except Exception as e:
            logger.error(f"run_in_blender执行出错: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise BlenderError(str(e))
            
    return wrapper()

class BlenderCommandHandler:
    """Blender command handler implementation"""
    
    def __init__(self):
        """Initialize the command handler"""
        self._handlers = {
            'get_scene_info': self.get_scene_info,
            'create_object': self.create_object,
            'delete_object': self.delete_object,
            'set_material': self.set_material,
            'get_object_info': self.get_object_info,
            'modify_object': self.modify_object,
            'execute_code': self.execute_code,
            'set_light_type': self.set_light_type,
            'set_light_energy': self.set_light_energy,
            'advanced_lighting': self.advanced_lighting,
            'set_active_camera': self.set_active_camera
        }
        
    def get_handlers(self) -> Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]]:
        """获取所有命令处理器
        
        Returns:
            Dict[str, Callable]: 命令处理器映射
        """
        return self._handlers
        
    @staticmethod
    async def create_object(params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new object in Blender"""
        try:
            logger.info(f"开始创建对象，参数: {params}")
            # 验证参数
            obj_type = params.get('object_type', 'MESH').upper()  # 使用object_type而不是type
            # 创建对象类型映射
            type_mapping = {
                'CUBE': 'MESH',
                'SPHERE': 'MESH',
                'CYLINDER': 'MESH',
                'CONE': 'MESH',
                'MESH': 'MESH',
                'CAMERA': 'CAMERA',
                'LIGHT': 'LIGHT',
                'EMPTY': 'EMPTY'
            }
            
            if obj_type not in type_mapping:
                raise ParameterError(f"Invalid object type: {obj_type}")
                
            object_name = params.get('object_name')
            location = params.get('location', (0, 0, 0))
            rotation = params.get('rotation', (0, 0, 0))
            scale = params.get('scale', (1, 1, 1))
            
            def create_object_sync():
                # 根据对象类型选择创建方法
                if obj_type == 'CUBE':
                    bpy.ops.mesh.primitive_cube_add(
                        location=location,
                        rotation=rotation,
                        scale=scale
                    )
                elif obj_type == 'SPHERE':
                    bpy.ops.mesh.primitive_uv_sphere_add(
                        location=location,
                        rotation=rotation,
                        scale=scale
                    )
                elif obj_type == 'CYLINDER':
                    bpy.ops.mesh.primitive_cylinder_add(
                        location=location,
                        rotation=rotation,
                        scale=scale
                    )
                elif obj_type == 'CONE':
                    bpy.ops.mesh.primitive_cone_add(
                        location=location,
                        rotation=rotation,
                        scale=scale
                    )
                elif obj_type == 'MESH':
                    bpy.ops.mesh.primitive_cube_add(  # 默认使用立方体
                        location=location,
                        rotation=rotation,
                        scale=scale
                    )
                elif obj_type == 'CAMERA':
                    bpy.ops.object.camera_add(
                        location=location,
                        rotation=rotation
                    )
                elif obj_type == 'LIGHT':
                    bpy.ops.object.light_add(
                        type='POINT',
                        location=location,
                        rotation=rotation
                    )
                elif obj_type == 'EMPTY':
                    bpy.ops.object.empty_add(
                        type='PLAIN_AXES',
                        location=location,
                        rotation=rotation
                    )
                
                obj = bpy.context.active_object
                if object_name:
                    obj.name = object_name
                    
                return {
                    'object_name': obj.name,
                    'type': obj.type,
                    'location': tuple(obj.location),
                    'rotation': tuple(obj.rotation_euler),
                    'scale': tuple(obj.scale)
                }
            
            # 在Blender主线程中执行
            return await run_in_blender(create_object_sync)
            
        except Exception as e:
            logger.exception("Error creating object")
            raise BlenderError(str(e))
            
    @staticmethod
    async def delete_object(params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an object from Blender"""
        try:
            logger.info(f"开始删除对象，参数: {params}")
            object_name = params.get('object_name')
            if not object_name:
                raise ParameterError("Object name is required")
                
            def delete_object_sync():
                obj = bpy.data.objects.get(object_name)
                if not obj:
                    raise BlenderError(f"Object not found: {object_name}")
                    
                bpy.data.objects.remove(obj, do_unlink=True)
                return {'status': 'success', 'message': f'Object {object_name} deleted'}
                
            return await run_in_blender(delete_object_sync)
            
        except Exception as e:
            logger.exception("Error deleting object")
            raise BlenderError(str(e))
            
    @staticmethod
    async def set_material(params: Dict[str, Any]) -> Dict[str, Any]:
        """设置对象材质
        
        Args:
            params: 命令参数
                - object_name: 对象名称
                - material: 材质名称 (可选)
                - color: 颜色值 [R,G,B,A] (可选，默认 [0.8,0.8,0.8,1.0])
                - metallic: 金属度 (可选，默认 0.0)
                - roughness: 粗糙度 (可选，默认 0.4)
                - specular: 镜面反射强度 (可选，默认 0.5)
                
        Returns:
            Dict[str, Any]: 设置结果
        """
        try:
            logger.info(f"开始设置材质，参数: {params}")
            
            # 验证必需参数
            if 'object_name' not in params:
                raise ParameterError("缺少必需的'object_name'参数")
            
            obj_name = params['object_name']
            if not isinstance(obj_name, str):
                raise ParameterError("'object_name'参数必须是字符串类型")
                
            # 验证可选参数
            material_name = params.get('material')
            if material_name is not None and not isinstance(material_name, str):
                raise ParameterError("'material'参数必须是字符串类型")
                
            color_value = params.get('color', [0.8, 0.8, 0.8, 1.0])
            if not isinstance(color_value, (list, tuple)):
                raise ParameterError("'color'参数必须是列表或元组类型")
                
            # 确保颜色值是4个分量
            if len(color_value) == 3:
                color_value = list(color_value) + [1.0]
            elif len(color_value) != 4:
                raise ParameterError("'color'参数必须包含3个或4个分量")
                
            # 验证颜色值范围
            for i, v in enumerate(color_value):
                if not isinstance(v, (int, float)):
                    raise ParameterError(f"颜色分量 {i} 必须是数字类型")
                if not 0 <= v <= 1:
                    raise ParameterError(f"颜色分量 {i} 必须在0到1之间")
                    
            # 验证其他可选参数
            metallic = params.get('metallic', 0.0)
            roughness = params.get('roughness', 0.4)
            specular = params.get('specular', 0.5)
            
            for param_name, param_value in [('metallic', metallic), ('roughness', roughness), ('specular', specular)]:
                if not isinstance(param_value, (int, float)):
                    raise ParameterError(f"'{param_name}'参数必须是数字类型")
                if not 0 <= param_value <= 1:
                    raise ParameterError(f"'{param_name}'参数必须在0到1之间")
            
            def set_material_sync():
                try:
                    # 获取对象
                    obj = bpy.data.objects.get(obj_name)
                    if not obj:
                        raise BlenderError(f"对象不存在: {obj_name}")
                        
                    # 创建或获取材质
                    mat = None
                    if material_name:
                        mat = bpy.data.materials.get(material_name)
                        if not mat:
                            mat = bpy.data.materials.new(name=material_name)
                            logger.debug(f"创建新材质: {material_name}")
                    else:
                        mat = bpy.data.materials.new(name=f"{obj_name}_material")
                        logger.debug(f"创建默认材质: {obj_name}_material")
                        
                    # 设置材质属性
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    
                    # 清除现有节点
                    nodes.clear()
                    
                    # 创建新的 Principled BSDF 节点
                    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                    bsdf.location = (0, 0)
                    
                    # 设置材质属性
                    bsdf.inputs['Base Color'].default_value = color_value
                    bsdf.inputs['Metallic'].default_value = metallic
                    bsdf.inputs['Roughness'].default_value = roughness
                    bsdf.inputs['Specular'].default_value = specular
                    
                    # 创建材质输出节点
                    output = nodes.new(type='ShaderNodeOutputMaterial')
                    output.location = (300, 0)
                    
                    # 连接节点
                    links = mat.node_tree.links
                    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                    
                    # 将材质分配给对象
                    if obj.data.materials:
                        # 更新现有材质槽
                        obj.data.materials[0] = mat
                        logger.debug(f"更新对象 {obj_name} 的材质: {mat.name}")
                    else:
                        # 添加新材质槽
                        obj.data.materials.append(mat)
                        logger.debug(f"添加材质到对象 {obj_name}: {mat.name}")
                        
                    # 确保所有材质槽都有材质
                    for slot in obj.material_slots:
                        if slot.material is None:
                            slot.material = mat
                            
                    return {
                        'success': True,
                        'material_name': mat.name,
                        'object_name': obj_name,
                        'properties': {
                            'color': color_value,
                            'metallic': metallic,
                            'roughness': roughness,
                            'specular': specular
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"设置材质属性时出错: {e}")
                    logger.error(f"错误堆栈:\n{traceback.format_exc()}")
                    raise BlenderError(f"设置材质属性失败: {str(e)}")
                    
            return await run_in_blender(set_material_sync)
            
        except Exception as e:
            logger.error(f"设置材质失败: {e}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise BlenderError(str(e))
            
    @staticmethod
    async def get_scene_info(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about the current scene"""
        try:
            logger.info("开始获取场景信息")
            
            def get_scene_info_sync():
                logger.debug("在主线程中执行get_scene_info_sync")
                try:
                    scene = bpy.context.scene
                    if not scene:
                        logger.error("无法获取当前场景")
                        raise BlenderError("无法获取当前场景")
                        
                    logger.debug(f"当前场景: {scene.name}")
                    objects = []
                    
                    for obj in scene.objects:
                        try:
                            obj_info = {
                                'object_name': obj.name,
                                'type': obj.type,
                                'location': tuple(obj.location),
                                'rotation': tuple(obj.rotation_euler),
                                'scale': tuple(obj.scale),
                                'visible': obj.visible_get()
                            }
                            
                            if obj.material_slots:
                                materials = []
                                for slot in obj.material_slots:
                                    if slot.material:
                                        materials.append(slot.material.name)
                                obj_info['materials'] = materials
                                
                            objects.append(obj_info)
                            logger.debug(f"已处理对象: {obj.name}")
                        except Exception as e:
                            logger.error(f"处理对象 {obj.name} 时出错: {e}")
                            logger.error(f"错误堆栈: {traceback.format_exc()}")
                            continue
                    
                    result = {
                        'scene_name': scene.name,
                        'objects': objects,
                        'frame_current': scene.frame_current,
                        'frame_start': scene.frame_start,
                        'frame_end': scene.frame_end
                    }
                    logger.debug(f"场景信息获取成功: {result}")
                    return result
                except Exception as e:
                    logger.error(f"获取场景信息时出错: {e}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    raise
                
            logger.info("准备在Blender主线程中执行get_scene_info_sync")
            result = await run_in_blender(get_scene_info_sync)
            logger.info("场景信息获取完成")
            return result
            
        except Exception as e:
            logger.error(f"获取场景信息失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise BlenderError(str(e))
            
    @staticmethod
    async def get_object_info(params: Dict[str, Any]) -> Dict[str, Any]:
        """获取对象信息
        
        Args:
            params: 命令参数
                - name: 对象名称
                
        Returns:
            Dict[str, Any]: 对象信息
        """
        try:
            logger.info(f"开始获取对象信息，参数: {params}")
            object_name = params.get('object_name')
            if not object_name:
                raise ParameterError("缺少对象名称")
                
            def get_object_info_sync():
                obj = bpy.data.objects.get(object_name)
                if not obj:
                    raise BlenderError(f"对象不存在: {object_name}")
                    
                return {
                    'object_name': obj.name,
                    'type': obj.type,
                    'location': list(obj.location),
                    'rotation': list(obj.rotation_euler),
                    'scale': list(obj.scale),
                    'dimensions': list(obj.dimensions),
                    'visible': obj.visible_get(),
                    'materials': [mat.name for mat in obj.data.materials] if obj.data and hasattr(obj.data, 'materials') else []
                }
                
            return await run_in_blender(get_object_info_sync)
            
        except Exception as e:
            logger.error(f"获取对象信息失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise BlenderError(str(e))
            
    @staticmethod
    async def modify_object(params: Dict[str, Any]) -> Dict[str, Any]:
        """修改对象
        
        Args:
            params: 命令参数
                - object_name: 对象名称
                - location: 位置 (可选)
                - rotation: 旋转 (可选)
                - scale: 缩放 (可选)
                - visible: 可见性 (可选)
                
        Returns:
            Dict[str, Any]: 修改结果
        """
        try:
            logger.info(f"开始修改对象，参数: {params}")
            
            # 验证必需参数
            if 'object_name' not in params:
                raise ParameterError("缺少必需的'object_name'参数")
            
            object_name = params['object_name']
            if not isinstance(object_name, str):
                raise ParameterError("'object_name'参数必须是字符串类型")
                
            # 验证可选参数的类型
            if 'location' in params:
                location = params['location']
                if not isinstance(location, (list, tuple)) or len(location) != 3:
                    raise ParameterError("'location'参数必须是包含3个元素的列表或元组")
                    
            if 'rotation' in params:
                rotation = params['rotation']
                if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
                    raise ParameterError("'rotation'参数必须是包含3个元素的列表或元组")
                    
            if 'scale' in params:
                scale = params['scale']
                if not isinstance(scale, (list, tuple)) or len(scale) != 3:
                    raise ParameterError("'scale'参数必须是包含3个元素的列表或元组")
                    
            if 'visible' in params:
                visible = params['visible']
                if not isinstance(visible, bool):
                    raise ParameterError("'visible'参数必须是布尔类型")
                
            def modify_object_sync():
                # 获取对象
                obj = bpy.data.objects.get(object_name)
                if not obj:
                    raise BlenderError(f"对象不存在: {object_name}")
                    
                try:
                    # 更新对象属性
                    if 'location' in params:
                        obj.location = params['location']
                        logger.debug(f"已更新对象位置: {params['location']}")
                        
                    if 'rotation' in params:
                        obj.rotation_euler = params['rotation']
                        logger.debug(f"已更新对象旋转: {params['rotation']}")
                        
                    if 'scale' in params:
                        obj.scale = params['scale']
                        logger.debug(f"已更新对象缩放: {params['scale']}")
                        
                    if 'visible' in params:
                        obj.hide_viewport = not params['visible']
                        obj.hide_render = not params['visible']
                        logger.debug(f"已更新对象可见性: {params['visible']}")
                        
                    return {
                        'success': True,
                        'message': f"对象已修改: {object_name}",
                        'object': {
                            'object_name': obj.name,
                            'type': obj.type,
                            'location': list(obj.location),
                            'rotation': list(obj.rotation_euler),
                            'scale': list(obj.scale),
                            'visible': obj.visible_get()
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"修改对象属性时出错: {e}")
                    logger.error(f"错误堆栈:\n{traceback.format_exc()}")
                    raise BlenderError(f"修改对象属性失败: {str(e)}")
                
            return await run_in_blender(modify_object_sync)
            
        except Exception as e:
            logger.error(f"修改对象失败: {e}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise BlenderError(str(e))
            
    async def execute_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Python代码
        
        Args:
            params: 命令参数
                - code: Python代码
                
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始执行Python代码，参数: {params}")
            
            # 验证code参数
            if 'code' not in params:
                raise ParameterError("缺少必需的'code'参数")
            
            code = params['code']
            if not isinstance(code, str):
                raise ParameterError("'code'参数必须是字符串类型")
                
            # 执行代码
            locals_dict = {}
            try:
                logger.debug(f"准备执行代码:\n{code}")
                exec(code, globals(), locals_dict)
                logger.debug("代码执行成功")
                
            except SyntaxError as e:
                logger.error(f"代码语法错误: {e}")
                logger.error(f"错误位置: 行 {e.lineno}, 列 {e.offset}")
                logger.error(f"错误文本: {e.text}")
                raise BlenderError(f"代码语法错误: 行 {e.lineno}, 列 {e.offset} - {str(e)}")
                
            except NameError as e:
                logger.error(f"未定义的变量: {e}")
                logger.error(f"错误堆栈:\n{traceback.format_exc()}")
                raise BlenderError(f"变量错误: {str(e)}")
                
            except Exception as e:
                logger.error(f"代码执行错误: {e}")
                logger.error(f"错误类型: {type(e).__name__}")
                logger.error(f"错误堆栈:\n{traceback.format_exc()}")
                raise BlenderError(f"执行错误 ({type(e).__name__}): {str(e)}")
            
            # 获取结果
            result = locals_dict.get('result')
            logger.debug(f"执行结果: {result}")
            
            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"执行代码失败: {e}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            raise BlenderError(str(e))
            
    @staticmethod
    async def set_light_type(params: Dict[str, Any]) -> Dict[str, Any]:
        """设置灯光类型"""
        try:
            logger.info(f"开始设置灯光类型，参数: {params}")
            object_name = params.get('object_name')
            light_type = params.get('light_type')
            if not object_name or not light_type:
                raise ParameterError("Object name and light type are required")

            def set_light_type_sync():
                obj = bpy.data.objects.get(object_name)
                if not obj or obj.type != 'LIGHT':
                    raise BlenderError(f"Object is not a light: {object_name}")
                
                obj.data.type = light_type
                return {
                    'object_name': object_name,
                    'light_type': light_type
                }

            return await run_in_blender(set_light_type_sync)

        except Exception as e:
            logger.error(f"设置灯光类型失败: {e}")
            raise BlenderError(str(e))

    @staticmethod
    async def set_light_energy(params: Dict[str, Any]) -> Dict[str, Any]:
        """设置灯光能量"""
        try:
            logger.info(f"开始设置灯光能量，参数: {params}")
            object_name = params.get('object_name')
            energy = params.get('energy')
            if not object_name or energy is None:
                raise ParameterError("Object name and energy are required")

            def set_light_energy_sync():
                obj = bpy.data.objects.get(object_name)
                if not obj or obj.type != 'LIGHT':
                    raise BlenderError(f"Object is not a light: {object_name}")
                
                obj.data.energy = float(energy)
                return {
                    'object_name': object_name,
                    'energy': energy
                }

            return await run_in_blender(set_light_energy_sync)

        except Exception as e:
            logger.error(f"设置灯光能量失败: {e}")
            raise BlenderError(str(e))

    @staticmethod
    async def advanced_lighting(params: Dict[str, Any]) -> Dict[str, Any]:
        """设置高级灯光参数"""
        try:
            logger.info(f"开始设置高级灯光参数，参数: {params}")
            object_name = params.get('object_name')
            light_type = params.get('light_type')
            location = params.get('location')
            energy = params.get('energy')
            color = params.get('color', [1.0, 1.0, 1.0])

            if not all([object_name, light_type, location, energy]):
                raise ParameterError("Missing required parameters")

            def advanced_lighting_sync():
                # 创建新的灯光
                bpy.ops.object.light_add(
                    type=light_type,
                    location=location
                )
                obj = bpy.context.active_object
                obj.name = object_name
                obj.data.energy = energy
                obj.data.color = color

                return {
                    'object_name': object_name,
                    'light_type': light_type,
                    'location': location,
                    'energy': energy,
                    'color': color
                }

            return await run_in_blender(advanced_lighting_sync)

        except Exception as e:
            logger.error(f"设置高级灯光参数失败: {e}")
            raise BlenderError(str(e))

    @staticmethod
    async def set_active_camera(params: Dict[str, Any]) -> Dict[str, Any]:
        """设置活动相机"""
        try:
            logger.info(f"开始设置活动相机，参数: {params}")
            object_name = params.get('object_name')
            if not object_name:
                raise ParameterError("Object name is required")

            def set_active_camera_sync():
                obj = bpy.data.objects.get(object_name)
                if not obj or obj.type != 'CAMERA':
                    raise BlenderError(f"Object is not a camera: {object_name}")
                
                bpy.context.scene.camera = obj
                return {
                    'object_name': object_name,
                    'active': True
                }

            return await run_in_blender(set_active_camera_sync)

        except Exception as e:
            logger.error(f"设置活动相机失败: {e}")
            raise BlenderError(str(e)) 