# 申论帮 - Python应用

from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
import os
import traceback
from datetime import timedelta

from src.config import config
from src.api.auth import auth_bp
from src.api.papers import papers_bp
from src.api.submissions import submissions_bp
from src.api.phrases import phrases_bp
from src.api.admin import admin_bp
from src.api.weak import weak_bp
from src.api.utils import api_error


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # 配置
    app.config['SECRET_KEY'] = config.jwt_secret
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

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
        return render_template('exam.html')

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
    def admin():
        if not session.get('admin_user'):
            return render_template('admin/login.html')
        return render_template('admin/dashboard.html')

    @app.route('/admin/login')
    def admin_login():
        return render_template('admin/login.html')

    @app.route('/admin/users')
    def admin_users():
        return render_template('admin/users.html')

    @app.route('/admin/papers')
    def admin_papers():
        return render_template('admin/papers.html')

    @app.route('/admin/phrases')
    def admin_phrases():
        return render_template('admin/phrases.html')

    @app.route('/admin/reviews')
    def admin_reviews():
        return render_template('admin/reviews.html')

    @app.route('/admin/stats')
    def admin_stats():
        return render_template('admin/stats.html')

    @app.route('/admin/logs')
    def admin_logs():
        return render_template('admin/logs.html')

    @app.route('/admin/settings')
    def admin_settings():
        return render_template('admin/settings.html')

    # 健康检查
    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'})

    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return api_error('Not found', 404)
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        traceback.print_exc()
        if request.path.startswith('/api/'):
            return api_error('Internal server error', 500)
        return render_template('500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)