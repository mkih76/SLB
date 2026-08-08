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

    # Config.DATABASE_PATH 是 import 时求值的类属性，
    # 必须在 create_app() 之前直接覆盖它，否则测试会打在真实库 data/slb.db 上
    from src.config import Config
    Config.DATABASE_PATH = db_path
    os.environ['DATABASE_PATH'] = db_path
    os.environ['TESTING'] = '1'

    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path

    yield app

    # 关闭 Flask app context 持有的 SQLite 连接，释放文件句柄（Windows 必需）
    with app.app_context():
        from flask import g
        if 'db' in g:
            g.db.close()
            g.pop('db', None)

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except PermissionError:
        # Windows 下文件句柄释放有延迟，宽限重试
        import time
        for _ in range(5):
            time.sleep(0.1)
            try:
                os.unlink(db_path)
                break
            except PermissionError:
                continue
    os.environ.pop('DATABASE_PATH', None)


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner"""
    return app.test_cli_runner()