# 申论帮 - Python应用

from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
import os
import logging
import traceback
from datetime import timedelta

from src.config import config
from src.api.auth import auth_bp
from src.api.papers import papers_bp
from src.api.submissions import submissions_bp
from src.api.phrases import phrases_bp
from src.api.admin import admin_bp
from src.api.weak import weak_bp
from src.api.utils import api_error, close_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


def admin_page_required(f):
    """管理后台页面鉴权装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_user'):
            return render_template('admin/login.html')
        return f(*args, **kwargs)
    return decorated


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # 配置
    app.config['SECRET_KEY'] = config.jwt_secret
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # CORS - restrict to configured origins
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '*')
    if allowed_origins != '*':
        allowed_origins = [o.strip() for o in allowed_origins.split(',')]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # 注册数据库连接关闭
    app.teardown_appcontext(close_db)

    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(papers_bp, url_prefix='/api/papers')
    app.register_blueprint(submissions_bp, url_prefix='/api/submissions')
    app.register_blueprint(phrases_bp, url_prefix='/api/phrases')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(weak_bp, url_prefix='/api/weak')

    # 页面路由
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/papers')
    def papers():
        return render_template('papers.html')

    @app.route('/exam/<pid>/<qid>')
    def exam(pid, qid):
        return render_template('exam.html', pid=pid, qid=qid)

    @app.route('/result/<sid>')
    def result(sid):
        return render_template('result.html', sid=sid)

    @app.route('/demo')
    def demo():
        return render_template('demo.html')

    @app.route('/phrases')
    def phrases_page():
        return render_template('phrases.html')

    # 管理后台
    @app.route('/admin')
    @admin_page_required
    def admin():
        return render_template('admin/dashboard.html')

    @app.route('/admin/login')
    def admin_login():
        return render_template('admin/login.html')

    @app.route('/admin/users')
    @admin_page_required
    def admin_users():
        return render_template('admin/users.html')

    @app.route('/admin/papers')
    @admin_page_required
    def admin_papers():
        return render_template('admin/papers.html')

    @app.route('/admin/phrases')
    @admin_page_required
    def admin_phrases():
        return render_template('admin/phrases.html')

    @app.route('/admin/reviews')
    @admin_page_required
    def admin_reviews():
        return render_template('admin/reviews.html')

    @app.route('/admin/stats')
    @admin_page_required
    def admin_stats():
        return render_template('admin/stats.html')

    @app.route('/admin/logs')
    @admin_page_required
    def admin_logs():
        return render_template('admin/logs.html')

    @app.route('/admin/settings')
    @admin_page_required
    def admin_settings():
        return render_template('admin/settings.html')

    # 健康检查
    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'})

    # 错误处理
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith('/api/'):
            return api_error('Bad request', 400)
        return render_template('404.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith('/api/'):
            return api_error('Forbidden', 403)
        return render_template('404.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return api_error('Not found', 404)
        return render_template('404.html'), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        if request.path.startswith('/api/'):
            return api_error('Method not allowed', 405)
        return render_template('404.html'), 405

    @app.errorhandler(413)
    def payload_too_large(e):
        if request.path.startswith('/api/'):
            return api_error('文件过大，最大16MB', 413)
        return render_template('404.html'), 413

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Internal server error: {traceback.format_exc()}")
        if request.path.startswith('/api/'):
            return api_error('Internal server error', 500)
        return render_template('500.html'), 500

    # 安全响应头
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    return app


app = create_app()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug)