"""公共测试 fixtures — 每个测试文件自动共享"""
import os
import sys
import pytest
import tempfile

# 确保 src 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import create_app


@pytest.fixture
def app():
    """创建测试用 Flask app（使用临时数据库）"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['TESTING'] = '1'

    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner"""
    return app.test_cli_runner()
