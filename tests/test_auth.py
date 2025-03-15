"""
BlenderMCP 认证管理器测试
"""

import pytest
import json
from src.blendermcp.common.errors import AuthError

@pytest.mark.asyncio
class TestAuth:
    """认证测试类"""
    
    async def test_login(self, server_connection):
        """测试登录"""
        # 发送登录请求
        await server_connection.send_json({
            'type': 'auth',
            'command': 'login',
            'username': 'test_admin',
            'password': 'admin123'
        })
        
        # 接收响应
        response = await server_connection.receive_json()
        assert response['type'] == 'auth'
        assert response['status'] == 'success'
        assert 'session_id' in response
        
    async def test_invalid_login(self, server_connection):
        """测试无效登录"""
        # 发送无效登录请求
        await server_connection.send_json({
            'type': 'auth',
            'command': 'login',
            'username': 'invalid_user',
            'password': 'wrong_password'
        })
        
        # 接收响应
        response = await server_connection.receive_json()
        assert response['type'] == 'auth'
        assert response['status'] == 'error'
        assert 'message' in response
        
    async def test_session_validation(self, server_connection):
        """测试会话验证"""
        # 先登录获取会话ID
        await server_connection.send_json({
            'type': 'auth',
            'command': 'login',
            'username': 'test_admin',
            'password': 'admin123'
        })
        login_response = await server_connection.receive_json()
        session_id = login_response['session_id']
        
        # 发送需要认证的命令
        await server_connection.send_json({
            'type': 'command',
            'command': 'get_scene_info',
            'session_id': session_id
        })
        
        # 接收响应
        response = await server_connection.receive_json()
        assert response['type'] == 'command'
        assert response['status'] == 'success'
        
    async def test_invalid_session(self, server_connection):
        """测试无效会话"""
        # 发送带无效会话ID的命令
        await server_connection.send_json({
            'type': 'command',
            'command': 'get_scene_info',
            'session_id': 'invalid_session_id'
        })
        
        # 接收响应
        response = await server_connection.receive_json()
        assert response['type'] == 'command'
        assert response['status'] == 'error'
        assert 'message' in response
        
    async def test_permission_check(self, server_connection):
        """测试权限检查"""
        # 使用普通用户登录
        await server_connection.send_json({
            'type': 'auth',
            'command': 'login',
            'username': 'test_user',
            'password': 'user123'
        })
        login_response = await server_connection.receive_json()
        session_id = login_response['session_id']
        
        # 尝试执行需要管理员权限的命令
        await server_connection.send_json({
            'type': 'command',
            'command': 'execute_code',
            'session_id': session_id,
            'code': 'print("test")'
        })
        
        # 接收响应
        response = await server_connection.receive_json()
        assert response['type'] == 'command'
        assert response['status'] == 'error'
        assert 'permission denied' in response['message'].lower()
        
    async def test_logout(self, server_connection):
        """测试注销"""
        # 先登录
        await server_connection.send_json({
            'type': 'auth',
            'command': 'login',
            'username': 'test_admin',
            'password': 'admin123'
        })
        login_response = await server_connection.receive_json()
        session_id = login_response['session_id']
        
        # 注销
        await server_connection.send_json({
            'type': 'auth',
            'command': 'logout',
            'session_id': session_id
        })
        
        # 接收响应
        response = await server_connection.receive_json()
        assert response['type'] == 'auth'
        assert response['status'] == 'success'
        
        # 尝试使用已注销的会话ID
        await server_connection.send_json({
            'type': 'command',
            'command': 'get_scene_info',
            'session_id': session_id
        })
        
        response = await server_connection.receive_json()
        assert response['type'] == 'command'
        assert response['status'] == 'error'
        assert 'invalid session' in response['message'].lower() 