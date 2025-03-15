"""
BlenderMCP Blender Command Handlers

This module implements handlers for Blender-related commands.
"""

import bpy
import asyncio
import logging
from typing import Dict, Any, Optional
from ...common.errors import BlenderError, ParameterError

logger = logging.getLogger(__name__)

class BlenderCommandHandler:
    """Handler for Blender commands"""
    
    @staticmethod
    async def create_object(params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new object in Blender"""
        try:
            # 验证参数
            obj_type = params.get('type', 'MESH')
            if obj_type not in {'MESH', 'CAMERA', 'LIGHT', 'EMPTY'}:
                raise ParameterError(f"Invalid object type: {obj_type}")
                
            name = params.get('name')
            location = params.get('location', (0, 0, 0))
            rotation = params.get('rotation', (0, 0, 0))
            scale = params.get('scale', (1, 1, 1))
            
            # 在主线程中执行Blender操作
            def create_object_sync():
                if obj_type == 'MESH':
                    bpy.ops.mesh.primitive_cube_add(
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
            
            # 在主线程中执行并返回结果
            return await asyncio.get_event_loop().run_in_executor(None, create_object_sync)
            
        except Exception as e:
            logger.exception("Error creating object")
            raise BlenderError(str(e))
            
    @staticmethod
    async def delete_object(params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an object from Blender"""
        try:
            name = params.get('name')
            if not name:
                raise ParameterError("Object name is required")
                
            def delete_object_sync():
                obj = bpy.data.objects.get(name)
                if not obj:
                    raise BlenderError(f"Object not found: {name}")
                    
                bpy.data.objects.remove(obj, do_unlink=True)
                return {'status': 'success', 'message': f'Object {name} deleted'}
                
            return await asyncio.get_event_loop().run_in_executor(None, delete_object_sync)
            
        except Exception as e:
            logger.exception("Error deleting object")
            raise BlenderError(str(e))
            
    @staticmethod
    async def set_material(params: Dict[str, Any]) -> Dict[str, Any]:
        """Set material for an object"""
        try:
            obj_name = params.get('object_name')
            if not obj_name:
                raise ParameterError("Object name is required")
                
            material_name = params.get('material_name')
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
                
            return await asyncio.get_event_loop().run_in_executor(None, set_material_sync)
            
        except Exception as e:
            logger.exception("Error setting material")
            raise BlenderError(str(e))
            
    @staticmethod
    async def get_scene_info(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about the current scene"""
        try:
            def get_scene_info_sync():
                scene = bpy.context.scene
                objects = []
                
                for obj in scene.objects:
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
                    
                return {
                    'scene_name': scene.name,
                    'objects': objects,
                    'frame_current': scene.frame_current,
                    'frame_start': scene.frame_start,
                    'frame_end': scene.frame_end
                }
                
            return await asyncio.get_event_loop().run_in_executor(None, get_scene_info_sync)
            
        except Exception as e:
            logger.exception("Error getting scene info")
            raise BlenderError(str(e)) 