"""
BlenderMCP Protocol Commands

This module defines the commands that can be sent between client and server.
"""

# 对象操作命令
CREATE_OBJECT = "create_object"
DELETE_OBJECT = "delete_object"
MODIFY_OBJECT = "modify_object"
GET_OBJECT_INFO = "get_object_info"

# 场景操作命令
GET_SCENE_INFO = "get_scene_info"

# 材质操作命令
SET_MATERIAL = "set_material"
SET_TEXTURE = "set_texture"

# 命令参数定义
PARAM_TYPE = "type"
PARAM_NAME = "name"
PARAM_LOCATION = "location"
PARAM_ROTATION = "rotation"
PARAM_SCALE = "scale"
PARAM_COLOR = "color"
PARAM_MATERIAL_NAME = "material_name"
PARAM_TEXTURE_ID = "texture_id" 