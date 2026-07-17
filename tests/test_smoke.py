"""基础冒烟测试 — 页面能加载、API 能响应"""
import pytest


class TestSmoke:
    """最基本的功能验证"""

    def test_homepage_loads(self, client):
        """首页能正常返回 200"""
        resp = client.get('/')
        assert resp.status_code == 200

    def test_papers_page_loads(self, client):
        """试卷列表页能正常返回"""
        resp = client.get('/papers')
        assert resp.status_code == 200

    def test_topics_page_loads(self, client):
        """热点列表页能正常返回"""
        resp = client.get('/topics')
        assert resp.status_code == 200

    def test_auth_register(self, client):
        """注册接口能正常响应"""
        resp = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'testpass123',
            'nickname': '测试用户',
        })
        # 可能 200/201 或 409（已存在），但不应 500
        assert resp.status_code in (200, 201, 409, 400)

    def test_auth_login(self, client):
        """登录接口能正常响应"""
        resp = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'testpass123',
        })
        # 可能 200 或 401，但不应 500
        assert resp.status_code in (200, 401)
