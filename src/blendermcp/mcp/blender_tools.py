"""
BlenderMCP Blender工具处理器

该模块提供了MCP工具的Blender实现，将MCP工具请求转换为Blender API调用。
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Union, Callable

# 尝试导入bpy，在测试环境中可能不可用
try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    
logger = logging.getLogger(__name__)

class BlenderToolHandler:
    """Blender工具处理器"""
    
    def __init__(self):
        """初始化处理器"""
        if not BLENDER_AVAILABLE:
            logger.warning("Blender API (bpy)不可用，工具将以模拟模式运行")
            
    async def handle_get_scene_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取场景信息工具
        
        Args:
            params: 工具参数
            
        Returns:
            场景信息结果
        """
        detailed = params.get("detailed", False)
        
        if not BLENDER_AVAILABLE:
            # 模拟模式返回
            return self._create_text_result("Blender API不可用，返回模拟数据。")
            
        try:
            # 获取当前场景
            scene = bpy.context.scene
            
            # 基本场景信息
            scene_info = {
                "name": scene.name,
                "frame_current": scene.frame_current,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "objects_count": len(scene.objects)
            }
            
            # 对象列表
            objects_info = []
            for obj in scene.objects:
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 4) for v in obj.location],
                    "visible": obj.visible_get()
                }
                
                # 详细模式下添加更多信息
                if detailed:
                    if obj.type == 'MESH' and obj.data:
                        obj_info["vertices_count"] = len(obj.data.vertices)
                        obj_info["polygons_count"] = len(obj.data.polygons)
                        
                    if obj.material_slots:
                        obj_info["materials"] = [slot.material.name if slot.material else "None" 
                                               for slot in obj.material_slots]
                
                objects_info.append(obj_info)
                
            # 材质列表
            materials_info = []
            for mat in bpy.data.materials:
                mat_info = {
                    "name": mat.name,
                    "use_nodes": mat.use_nodes
                }
                materials_info.append(mat_info)
                
            # 灯光列表
            lights_info = []
            for light in bpy.data.lights:
                light_info = {
                    "name": light.name,
                    "type": light.type,
                    "energy": round(light.energy, 2),
                    "color": [round(c, 4) for c in light.color]
                }
                lights_info.append(light_info)
                
            # 相机列表
            cameras_info = []
            for camera in bpy.data.cameras:
                camera_info = {
                    "name": camera.name,
                    "lens": round(camera.lens, 2),
                    "clip_start": round(camera.clip_start, 4),
                    "clip_end": round(camera.clip_end, 4)
                }
                cameras_info.append(camera_info)
                
            # 渲染设置
            render_info = {
                "engine": scene.render.engine,
                "resolution_x": scene.render.resolution_x,
                "resolution_y": scene.render.resolution_y,
                "fps": scene.render.fps
            }
            
            # 组装结果
            result = {
                "scene": scene_info,
                "objects": objects_info,
                "materials": materials_info,
                "lights": lights_info,
                "cameras": cameras_info,
                "render": render_info
            }
            
            # 创建响应
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"获取到场景'{scene.name}'的信息，包含{len(objects_info)}个对象。"
                    },
                    {
                        "type": "json",
                        "json": result
                    }
                ]
            }
            
        except Exception as e:
            logger.exception(f"获取场景信息失败: {e}")
            return self._create_error_result(f"获取场景信息失败: {str(e)}")
            
    async def handle_create_object(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理创建对象工具
        
        Args:
            params: 工具参数
            
        Returns:
            创建结果
        """
        obj_type = params.get("type", "MESH")
        obj_name = params.get("name", "")
        location = params.get("location", [0, 0, 0])
        
        if not BLENDER_AVAILABLE:
            # 模拟模式返回
            return self._create_text_result(f"Blender API不可用，模拟创建{obj_type}对象: {obj_name}")
            
        try:
            # 根据类型创建不同对象
            if obj_type == "MESH":
                # 创建基础网格
                mesh_type = params.get("mesh_type", "CUBE").upper()
                
                if mesh_type == "CUBE":
                    bpy.ops.mesh.primitive_cube_add(size=2.0, location=location)
                elif mesh_type == "SPHERE":
                    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=location)
                elif mesh_type == "CYLINDER":
                    bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0, location=location)
                elif mesh_type == "PLANE":
                    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location)
                else:
                    # 默认创建立方体
                    bpy.ops.mesh.primitive_cube_add(size=2.0, location=location)
                    
            elif obj_type == "LIGHT":
                # 创建灯光
                light_type = params.get("light_type", "POINT").upper()
                
                if light_type == "POINT":
                    bpy.ops.object.light_add(type='POINT', location=location)
                elif light_type == "SUN":
                    bpy.ops.object.light_add(type='SUN', location=location)
                elif light_type == "SPOT":
                    bpy.ops.object.light_add(type='SPOT', location=location)
                elif light_type == "AREA":
                    bpy.ops.object.light_add(type='AREA', location=location)
                else:
                    # 默认创建点光源
                    bpy.ops.object.light_add(type='POINT', location=location)
                    
            elif obj_type == "CAMERA":
                # 创建相机
                bpy.ops.object.camera_add(location=location)
                
            elif obj_type == "EMPTY":
                # 创建空对象
                empty_type = params.get("empty_type", "PLAIN_AXES").upper()
                bpy.ops.object.empty_add(type=empty_type, location=location)
                
            elif obj_type == "CURVE":
                # 创建曲线
                curve_type = params.get("curve_type", "BEZIER").upper()
                
                if curve_type == "BEZIER":
                    bpy.ops.curve.primitive_bezier_curve_add(location=location)
                elif curve_type == "CIRCLE":
                    bpy.ops.curve.primitive_bezier_circle_add(location=location)
                else:
                    # 默认创建贝塞尔曲线
                    bpy.ops.curve.primitive_bezier_curve_add(location=location)
            else:
                return self._create_error_result(f"不支持的对象类型: {obj_type}")
                
            # 设置对象名称
            if obj_name:
                bpy.context.active_object.name = obj_name
                
            # 获取创建的对象
            created_obj = bpy.context.active_object
            
            # 创建响应
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"成功创建{obj_type}对象: {created_obj.name}"
                    },
                    {
                        "type": "json",
                        "json": {
                            "name": created_obj.name,
                            "type": created_obj.type,
                            "location": [round(v, 4) for v in created_obj.location]
                        }
                    }
                ]
            }
            
        except Exception as e:
            logger.exception(f"创建对象失败: {e}")
            return self._create_error_result(f"创建对象失败: {str(e)}")
            
    async def handle_delete_object(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理删除对象工具
        
        Args:
            params: 工具参数
            
        Returns:
            删除结果
        """
        obj_name = params.get("name", "")
        
        if not obj_name:
            return self._create_error_result("未指定对象名称")
            
        if not BLENDER_AVAILABLE:
            # 模拟模式返回
            return self._create_text_result(f"Blender API不可用，模拟删除对象: {obj_name}")
            
        try:
            # 查找对象
            obj = bpy.data.objects.get(obj_name)
            
            if not obj:
                return self._create_error_result(f"对象不存在: {obj_name}")
                
            # 删除对象
            bpy.data.objects.remove(obj)
            
            # 创建响应
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"成功删除对象: {obj_name}"
                    }
                ]
            }
            
        except Exception as e:
            logger.exception(f"删除对象失败: {e}")
            return self._create_error_result(f"删除对象失败: {str(e)}")
            
    async def handle_set_material(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理设置材质工具
        
        Args:
            params: 工具参数
            
        Returns:
            设置结果
        """
        obj_name = params.get("object_name", "")
        material_name = params.get("material_name", "")
        create_new = params.get("create_new", True)
        color = params.get("color", [0.8, 0.8, 0.8, 1.0])
        
        if not obj_name:
            return self._create_error_result("未指定对象名称")
            
        if not BLENDER_AVAILABLE:
            # 模拟模式返回
            return self._create_text_result(f"Blender API不可用，模拟设置材质: {obj_name} -> {material_name}")
            
        try:
            # 查找对象
            obj = bpy.data.objects.get(obj_name)
            
            if not obj:
                return self._create_error_result(f"对象不存在: {obj_name}")
                
            # 查找或创建材质
            mat = None
            if material_name and not create_new:
                mat = bpy.data.materials.get(material_name)
                
            if not mat:
                # 创建新材质
                mat = bpy.data.materials.new(name=material_name or f"Material_{obj.name}")
                mat.use_nodes = True
                
                # 设置基础颜色
                if color and len(color) >= 3:
                    # 确保颜色是有效的RGBA值
                    rgba = color + [1.0] if len(color) == 3 else color
                    rgba = [max(0, min(1, c)) for c in rgba]  # 限制在[0,1]范围内
                    
                    # 获取材质输出节点
                    principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
                    if principled_bsdf:
                        principled_bsdf.inputs[0].default_value = rgba
                
            # 应用材质到对象
            if len(obj.material_slots) == 0:
                obj.data.materials.append(mat)
            else:
                obj.material_slots[0].material = mat
                
            # 创建响应
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"成功为对象'{obj.name}'设置材质'{mat.name}'"
                    }
                ]
            }
            
        except Exception as e:
            logger.exception(f"设置材质失败: {e}")
            return self._create_error_result(f"设置材质失败: {str(e)}")
            
    async def handle_render_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理渲染图像工具
        
        Args:
            params: 工具参数
            
        Returns:
            渲染结果
        """
        output_path = params.get("output_path", "//render.png")
        resolution_x = params.get("resolution_x", 1920)
        resolution_y = params.get("resolution_y", 1080)
        
        if not BLENDER_AVAILABLE:
            # 模拟模式返回
            return self._create_text_result(f"Blender API不可用，模拟渲染图像: {output_path}")
            
        try:
            # 设置渲染参数
            scene = bpy.context.scene
            scene.render.resolution_x = resolution_x
            scene.render.resolution_y = resolution_y
            scene.render.filepath = output_path
            scene.render.image_settings.file_format = 'PNG'
            
            # 执行渲染
            bpy.ops.render.render(write_still=True)
            
            # 创建响应
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"成功渲染图像: {output_path}"
                    },
                    {
                        "type": "json",
                        "json": {
                            "output_path": output_path,
                            "resolution": [resolution_x, resolution_y]
                        }
                    }
                ]
            }
            
        except Exception as e:
            logger.exception(f"渲染图像失败: {e}")
            return self._create_error_result(f"渲染图像失败: {str(e)}")
            
    # 辅助方法
    
    def _create_text_result(self, text: str) -> Dict[str, Any]:
        """创建文本结果
        
        Args:
            text: 文本内容
            
        Returns:
            结果对象
        """
        return {
            "content": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
        
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果
        
        Args:
            error_message: 错误消息
            
        Returns:
            错误结果对象
        """
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": error_message
                }
            ]
        } 