"""
BlenderMCP 认证模块

本模块提供认证和访问控制功能。
"""

import logging
import hashlib
import secrets
from typing import Dict, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        """初始化认证管理器"""
        self.users: Dict[str, Dict] = {}  # 用户信息
        self.sessions: Dict[str, Dict] = {}  # 会话信息
        self.permissions: Dict[str, Set[str]] = {}  # 权限配置
        self.session_timeout = timedelta(hours=1)  # 会话超时时间
        
    def add_user(self, username: str, password: str, role: str = 'user'):
        """添加用户
        
        Args:
            username: 用户名
            password: 密码
            role: 用户角色
        """
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        
        self.users[username] = {
            'password_hash': password_hash,
            'salt': salt,
            'role': role,
            'created_at': datetime.now()
        }
        
        # 设置默认权限
        if role not in self.permissions:
            self.permissions[role] = set()
            
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """验证用户身份
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Optional[str]: 成功返回会话ID，失败返回None
        """
        user = self.users.get(username)
        if not user:
            logger.warning(f"用户不存在: {username}")
            return None
            
        password_hash = self._hash_password(password, user['salt'])
        if password_hash != user['password_hash']:
            logger.warning(f"密码错误: {username}")
            return None
            
        # 创建新会话
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'username': username,
            'role': user['role'],
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        
        return session_id
        
    def validate_session(self, session_id: str) -> bool:
        """验证会话是否有效
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 会话是否有效
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
            
        # 检查会话是否过期
        if datetime.now() - session['last_activity'] > self.session_timeout:
            self.sessions.pop(session_id)
            return False
            
        # 更新最后活动时间
        session['last_activity'] = datetime.now()
        return True
        
    def check_permission(self, session_id: str, permission: str) -> bool:
        """检查用户是否有指定权限
        
        Args:
            session_id: 会话ID
            permission: 权限名称
            
        Returns:
            bool: 是否有权限
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
            
        role = session['role']
        role_permissions = self.permissions.get(role, set())
        
        # 管理员角色拥有所有权限
        if role == 'admin':
            return True
            
        return permission in role_permissions
        
    def add_permission(self, role: str, permission: str):
        """添加角色权限
        
        Args:
            role: 角色名称
            permission: 权限名称
        """
        if role not in self.permissions:
            self.permissions[role] = set()
        self.permissions[role].add(permission)
        
    def remove_permission(self, role: str, permission: str):
        """移除角色权限
        
        Args:
            role: 角色名称
            permission: 权限名称
        """
        if role in self.permissions:
            self.permissions[role].discard(permission)
            
    def logout(self, session_id: str):
        """注销会话
        
        Args:
            session_id: 会话ID
        """
        self.sessions.pop(session_id, None)
        
    def cleanup_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if current_time - session['last_activity'] > self.session_timeout
        ]
        for sid in expired_sessions:
            self.sessions.pop(sid)
            
    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """计算密码哈希值
        
        Args:
            password: 密码
            salt: 盐值
            
        Returns:
            str: 哈希值
        """
        combined = password + salt
        return hashlib.sha256(combined.encode()).hexdigest()
        
class Permission:
    """权限常量"""
    
    # 对象操作权限
    CREATE_OBJECT = 'create_object'
    DELETE_OBJECT = 'delete_object'
    MODIFY_OBJECT = 'modify_object'
    
    # 材质操作权限
    SET_MATERIAL = 'set_material'
    
    # 场景操作权限
    GET_SCENE_INFO = 'get_scene_info'
    GET_OBJECT_INFO = 'get_object_info'
    
    # 代码执行权限
    EXECUTE_CODE = 'execute_code'
    
    # 灯光操作权限
    SET_LIGHT = 'set_light'
    
    # 相机操作权限
    SET_CAMERA = 'set_camera'
    
    # 文件操作权限
    READ_FILE = 'read_file'
    WRITE_FILE = 'write_file'
    DELETE_FILE = 'delete_file'
    
    # 系统操作权限
    SYSTEM_CONFIG = 'system_config'
    USER_MANAGE = 'user_manage' 