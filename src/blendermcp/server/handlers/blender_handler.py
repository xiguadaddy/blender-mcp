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
            'execute_code': self.execute_code
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
            obj_type = params.get('type', 'MESH').upper()  # 转换为大写
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
                
            name = params.get('name')
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
                if name:
                    obj.name = name
                    
                return {
                    'name': obj.name,
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
            name = params.get('name')
            if not name:
                raise ParameterError("Object name is required")
                
            def delete_object_sync():
                obj = bpy.data.objects.get(name)
                if not obj:
                    raise BlenderError(f"Object not found: {name}")
                    
                bpy.data.objects.remove(obj, do_unlink=True)
                return {'status': 'success', 'message': f'Object {name} deleted'}
                
            return await run_in_blender(delete_object_sync)
            
        except Exception as e:
            logger.exception("Error deleting object")
            raise BlenderError(str(e))
            
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
            color_value = list(params.get('color', (0.8, 0.8, 0.8, 1.0)))  # 转换为列表以便修改
            if len(color_value) == 3:
                color_value.append(1.0)  # 在外部作用域添加 alpha 通道
            
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
                
                # 清除现有节点
                nodes.clear()
                
                # 创建新的 Principled BSDF 节点
                bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                bsdf.location = (0, 0)
                
                # 创建材质输出节点
                output = nodes.new(type='ShaderNodeOutputMaterial')
                output.location = (300, 0)
                
                # 连接节点
                links = mat.node_tree.links
                links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                
                # 设置颜色
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
                                'name': obj.name,
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
            obj_name = params.get('name')
            if not obj_name:
                raise ParameterError("缺少对象名称")
                
            def get_object_info_sync():
                obj = bpy.data.objects.get(obj_name)
                if not obj:
                    raise BlenderError(f"对象不存在: {obj_name}")
                    
                return {
                    'name': obj.name,
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
                - name: 对象名称
                - location: 位置
                - rotation: 旋转
                - scale: 缩放
                - visible: 可见性
                
        Returns:
            Dict[str, Any]: 修改结果
        """
        try:
            logger.info(f"开始修改对象，参数: {params}")
            obj_name = params.get('name')
            if not obj_name:
                raise ParameterError("缺少对象名称")
                
            def modify_object_sync():
                obj = bpy.data.objects.get(obj_name)
                if not obj:
                    raise BlenderError(f"对象不存在: {obj_name}")
                    
                # 更新对象属性
                if 'location' in params:
                    obj.location = params['location']
                if 'rotation' in params:
                    obj.rotation_euler = params['rotation']
                if 'scale' in params:
                    obj.scale = params['scale']
                if 'visible' in params:
                    obj.hide_viewport = not params['visible']
                    obj.hide_render = not params['visible']
                    
                return {
                    'success': True,
                    'message': f"对象已修改: {obj_name}",
                    'object': {
                        'name': obj.name,
                        'type': obj.type,
                        'location': list(obj.location),
                        'rotation': list(obj.rotation_euler),
                        'scale': list(obj.scale),
                        'visible': obj.visible_get()
                    }
                }
                
            return await run_in_blender(modify_object_sync)
            
        except Exception as e:
            logger.error(f"修改对象失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
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
            code = params.get('code')
            if not code:
                raise ValueError("缺少代码")
                
            # 执行代码
            locals_dict = {}
            exec(code, globals(), locals_dict)
            
            # 获取结果
            result = locals_dict.get('result')
            
            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"执行代码失败: {e}")
            raise 