"""
模拟Blender Python API (bpy)模块
"""

class Object:
    """模拟Blender对象"""
    
    def __init__(self, name="", type="MESH"):
        self.name = name
        self.type = type
        self.location = (0, 0, 0)
        self.rotation_euler = (0, 0, 0)
        self.scale = (1, 1, 1)
        self.data = None
        
class Mesh:
    """模拟Blender网格"""
    
    def __init__(self, name=""):
        self.name = name
        self.vertices = []
        self.edges = []
        self.faces = []
        
class Material:
    """模拟Blender材质"""
    
    def __init__(self, name=""):
        self.name = name
        self.use_nodes = False
        self.node_tree = None
        
class Scene:
    """模拟Blender场景"""
    
    def __init__(self, name="Scene"):
        self.name = name
        self.objects = []
        
class Context:
    """模拟Blender上下文"""
    
    def __init__(self):
        self.scene = Scene()
        self.object = None
        self.selected_objects = []
        
class Data:
    """模拟Blender数据"""
    
    def __init__(self):
        self.objects = []
        self.meshes = []
        self.materials = []
        self.scenes = [Scene()]
        
class Ops:
    """模拟Blender操作"""
    
    class object:
        @staticmethod
        def add(type="MESH", location=(0, 0, 0)):
            """添加对象"""
            obj = Object(name=f"Object_{len(data.objects)}", type=type)
            obj.location = location
            data.objects.append(obj)
            return {"FINISHED"}
            
        @staticmethod
        def delete():
            """删除对象"""
            return {"FINISHED"}
            
    class mesh:
        @staticmethod
        def primitive_cube_add(size=2.0, location=(0, 0, 0)):
            """添加立方体"""
            mesh = Mesh(name=f"Cube_{len(data.meshes)}")
            data.meshes.append(mesh)
            
            obj = Object(name=f"Cube_{len(data.objects)}", type="MESH")
            obj.location = location
            obj.data = mesh
            data.objects.append(obj)
            return {"FINISHED"}
            
        @staticmethod
        def primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0)):
            """添加UV球体"""
            mesh = Mesh(name=f"Sphere_{len(data.meshes)}")
            data.meshes.append(mesh)
            
            obj = Object(name=f"Sphere_{len(data.objects)}", type="MESH")
            obj.location = location
            obj.data = mesh
            data.objects.append(obj)
            return {"FINISHED"}
            
    class material:
        @staticmethod
        def new(name="Material"):
            """创建新材质"""
            mat = Material(name=name)
            data.materials.append(mat)
            return mat
            
    class render:
        @staticmethod
        def render(animation=False):
            """渲染"""
            return {"FINISHED"}
            
        @staticmethod
        def view_layer_update():
            """更新视图层"""
            return {"FINISHED"}
            
class Types:
    """模拟Blender类型"""
    
    class Object(Object):
        pass
        
    class Mesh(Mesh):
        pass
        
    class Material(Material):
        pass
        
    class Scene(Scene):
        pass
        
# 创建全局实例
context = Context()
data = Data()
ops = Ops()
types = Types()

# 导出模块变量
__all__ = ['context', 'data', 'ops', 'types'] 