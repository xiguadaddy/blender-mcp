"""
BlenderMCP 插件安装脚本

自动检测 Blender 版本并安装插件到正确的目录
支持 Windows, macOS 和 Linux
"""

import os
import sys
import shutil
import logging
import subprocess
import tempfile
import platform
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_platform_specific_paths():
    """获取平台特定的Blender安装路径"""
    system = platform.system().lower()
    
    if system == 'windows':
        return [
            os.path.expanduser("~\\AppData\\Roaming\\Blender Foundation\\Blender"),  # 用户目录
        ]
    elif system == 'darwin':  # macOS
        return [
            os.path.expanduser("~/Library/Application Support/Blender"),
        ]
    else:  # Linux
        return [
            os.path.expanduser("~/.config/blender"),
        ]

def get_blender_versions():
    """获取已安装的 Blender 版本"""
    possible_paths = get_platform_specific_paths()
    versions = []
    
    for base_path in possible_paths:
        if not os.path.exists(base_path):
            continue
            
        try:
            # 遍历目录查找Blender版本
            for item in os.listdir(base_path):
                if item.replace(".", "").isdigit():  # 检查是否是版本号目录（如 "4.2"）
                    version = item
                    addon_path = os.path.join(base_path, version, "scripts", "addons")
                    
                    # 确保插件目录存在
                    os.makedirs(addon_path, exist_ok=True)
                    if os.access(addon_path, os.W_OK):
                        versions.append((version, addon_path))
                        logger.info(f"找到 Blender {version} 插件目录: {addon_path}")
                    
        except Exception as e:
            logger.warning(f"检查目录 {base_path} 时出错: {e}")
    
    # 如果没有找到任何版本，创建默认版本目录
    if not versions:
        logger.warning("未找到插件目录，将创建默认目录")
        default_versions = ["4.2", "3.6", "2.93"]  # 支持的版本列表
        
        for version in default_versions:
            try:
                if platform.system().lower() == 'windows':
                    addon_path = os.path.expanduser(f"~\\AppData\\Roaming\\Blender Foundation\\Blender\\{version}\\scripts\\addons")
                elif platform.system().lower() == 'darwin':
                    addon_path = os.path.expanduser(f"~/Library/Application Support/Blender/{version}/scripts/addons")
                else:  # Linux
                    addon_path = os.path.expanduser(f"~/.config/blender/{version}/scripts/addons")
                
                os.makedirs(addon_path, exist_ok=True)
                versions.append((version, addon_path))
                logger.info(f"已创建插件目录: {addon_path}")
                break  # 成功创建一个目录后就退出
            except Exception as e:
                continue
    
    return versions

def get_addon_source_path():
    """获取插件源代码路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(os.path.dirname(current_dir), "src", "blendermcp")
    return source_path

def get_addon_install_path(blender_version):
    """获取插件安装路径"""
    versions = get_blender_versions()
    for version, addons_path in versions:
        if version == blender_version:
            return os.path.join(addons_path, "blendermcp")
    
    # 如果没有找到指定版本，使用第一个可用的版本
    if versions:
        logger.warning(f"未找到Blender {blender_version}，将使用版本 {versions[0][0]}")
        return os.path.join(versions[0][1], "blendermcp")
    
    return None

def get_blender_python_path(blender_version):
    """获取 Blender Python 路径"""
    system = platform.system().lower()
    if system == 'windows':
        return os.path.expanduser(f"~\\AppData\\Roaming\\Blender Foundation\\Blender\\{blender_version}\\python\\bin\\python.exe")
    elif system == 'darwin':
        return f"/Applications/Blender.app/Contents/Resources/{blender_version}/python/bin/python3"
    else:  # Linux
        return f"/usr/share/blender/{blender_version}/python/bin/python3"

def get_system_python():
    """获取系统 Python 路径"""
    try:
        # 尝试使用 py launcher
        result = subprocess.check_output(['py', '-3', '-c', 'import sys; print(sys.executable)'])
        return result.decode().strip()
    except:
        try:
            # 尝试使用 python 命令
            result = subprocess.check_output(['python', '-c', 'import sys; print(sys.executable)'])
            return result.decode().strip()
        except:
            return None

def install_dependencies_to_temp():
    """安装依赖到临时目录"""
    temp_dir = tempfile.mkdtemp()
    try:
        requirements_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requirements.txt")
        if not os.path.exists(requirements_file):
            logger.error("找不到 requirements.txt 文件")
            return None
        
        python_exe = get_system_python()
        if not python_exe:
            logger.error("找不到系统 Python")
            return None
        
        try:
            subprocess.check_call([python_exe, "-m", "pip", "install", 
                                 "--target", temp_dir, 
                                 "-r", requirements_file])
            return temp_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"安装依赖时出错: {e}")
            return None
    except Exception as e:
        logger.error(f"创建临时目录时出错: {e}")
        return None

def copy_dependencies(temp_dir, install_path):
    """复制依赖到插件目录"""
    if not temp_dir or not os.path.exists(temp_dir):
        logger.error("临时目录不存在")
        return
    
    try:
        # 创建 lib 目录
        lib_path = os.path.join(install_path, "lib")
        os.makedirs(lib_path, exist_ok=True)
        
        # 复制所有依赖包到 lib 目录
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path) and not item.startswith('__'):
                target_path = os.path.join(lib_path, item)
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                shutil.copytree(item_path, target_path)
            elif os.path.isfile(item_path) and item.endswith('.py'):
                shutil.copy2(item_path, lib_path)
        
        # 创建 __init__.py
        init_file = os.path.join(lib_path, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('"""Dependencies package."""\n')
        
        logger.info("依赖包已复制到插件目录")
    except Exception as e:
        logger.error(f"复制依赖时出错: {e}")
    finally:
        try:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"清理临时目录时出错: {e}")

def modify_addon_init(install_path):
    """修改插件的 __init__.py 文件，添加依赖路径"""
    init_file = os.path.join(install_path, "__init__.py")
    if not os.path.exists(init_file):
        return
    
    try:
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 添加依赖路径代码
        path_setup = '''
import os
import sys

# 添加依赖路径
lib_path = os.path.join(os.path.dirname(__file__), "lib")
if os.path.exists(lib_path) and lib_path not in sys.path:
    sys.path.insert(0, lib_path)
'''
        
        # 如果文件开头没有这段代码，就添加它
        if "lib_path = os.path.join(os.path.dirname(__file__)" not in content:
            content = path_setup + content
            
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("已更新插件初始化文件")
    except Exception as e:
        logger.error(f"修改插件初始化文件时出错: {e}")

def uninstall_addon(blender_version):
    """卸载插件"""
    install_path = get_addon_install_path(blender_version)
    if os.path.exists(install_path):
        try:
            shutil.rmtree(install_path)
            logger.info(f"插件已从 Blender {blender_version} 卸载")
        except Exception as e:
            logger.error(f"卸载插件时出错: {e}")

def install_addon(blender_version):
    """安装插件"""
    source_path = get_addon_source_path()
    install_path = get_addon_install_path(blender_version)
    
    # 确保源代码路径存在
    if not os.path.exists(source_path):
        logger.error("找不到插件源代码")
        return False
    
    try:
        # 如果目标目录已存在，先删除
        if os.path.exists(install_path):
            shutil.rmtree(install_path)
        
        # 创建插件目录
        os.makedirs(install_path)
        
        # 复制整个 blendermcp 包到插件目录
        for item in os.listdir(source_path):
            src = os.path.join(source_path, item)
            dst = os.path.join(install_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        # 安装依赖
        temp_dir = install_dependencies_to_temp()
        if temp_dir:
            copy_dependencies(temp_dir, install_path)
            
        # 修改插件初始化文件
        modify_addon_init(install_path)
        
        logger.info(f"插件已成功安装到 Blender {blender_version}")
        return True
        
    except Exception as e:
        logger.error(f"安装插件时出错: {e}")
        return False

def main():
    """主函数"""
    # 获取命令行参数
    uninstall = "--uninstall" in sys.argv
    
    # 获取 Blender 版本
    versions = get_blender_versions()
    if not versions:
        logger.error("未找到已安装的 Blender")
        return
    
    logger.info(f"找到以下 Blender 版本: {', '.join([version for version, _ in versions])}")
    
    # 对每个版本进行操作
    for version, _ in versions:
        logger.info(f"将在以下版本上操作: {version}")
        if uninstall:
            uninstall_addon(version)
        else:
            install_addon(version)

if __name__ == "__main__":
    main() 