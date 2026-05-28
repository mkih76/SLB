# 申论帮 - 唯一入口文件
# 生产环境通过 gunicorn app:app 启动

import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, send_from_directory, abort, request
from flask_cors import CORS

from src.config import Config
from src.api.utils import init_db, close_db
from src.api.auth import auth_bp
from src.api.papers import papers_bp
from src.api.submissions import submissions_bp
from src.api.phrases import phrases_bp
from src.api.admin import admin_bp
from src.api.weak import weak_bp
from src.api.drill import drill_bp
from src.api.diagnosis import diagnosis_bp
from src.api.simulation import simulation_bp
from src.api.plan import plan_bp
from src.api.topic import topic_bp
from src.api.community import community_bp

import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    app.config.from_object(Config)

    # CORS
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '*')
    if allowed_origins != '*':
        allowed_origins = [o.strip() for o in allowed_origins.split(',')]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # Register database close
    app.teardown_appcontext(close_db)

    # Register all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(papers_bp)
    app.register_blueprint(submissions_bp)
    app.register_blueprint(phrases_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(weak_bp)
    app.register_blueprint(drill_bp)
    app.register_blueprint(diagnosis_bp)
    app.register_blueprint(simulation_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(topic_bp)
    app.register_blueprint(community_bp)

    # Initialize database on first request
    with app.app_context():
        init_db()

    # Performance monitoring
    @app.before_request
    def start_timer():
        request._start_time = time.time()

    @app.after_request
    def log_request(response):
        if hasattr(request, '_start_time'):
            elapsed = time.time() - request._start_time
            if elapsed > 2.0:
                logger.warning(f"Slow request: {request.method} {request.path} took {elapsed:.2f}s")
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Page routes
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

    @app.route('/drill')
    def drill():
        return render_template('drill.html')

    @app.route('/diagnosis')
    def diagnosis():
        return render_template('diagnosis.html')

    @app.route('/simulate/<pid>')
    def simulate(pid):
        return render_template('simulate.html', pid=pid)

    @app.route('/phrases')
    def phrases_page():
        return render_template('phrases.html')

    @app.route('/phrases/study')
    def phrases_study():
        return render_template('phrases_study.html')

    @app.route('/phrases/generate')
    def phrases_generate():
        return render_template('phrases_generate.html')

    @app.route('/plan')
    def plan():
        return render_template('plan.html')

    @app.route('/topics')
    def topics():
        return render_template('topics.html')

    @app.route('/topics/<int:topic_id>')
    def topic_detail(topic_id):
        import jwt
        from src.config import JWT_SECRET, JWT_ALGORITHM
        from src.services import topic_service
        uid = None
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            try:
                data = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
                uid = data.get('sub')
            except Exception:
                pass
        topic = topic_service.get_topic_detail(topic_id, uid)
        if not topic:
            abort(404)
        return render_template('topic_detail.html', topic=topic)

    @app.route('/community')
    def community():
        return render_template('community.html')

    # Admin routes
    @app.route('/admin')
    def admin_index():
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

    # Health check
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    # SEO files
    @app.route('/sitemap.xml')
    def sitemap():
        return send_from_directory(app.static_folder, 'sitemap.xml', mimetype='application/xml')

    @app.route('/robots.txt')
    def robots():
        return send_from_directory(app.static_folder, 'robots.txt', mimetype='text/plain')

    # Favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/x-icon')

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return {'error': 'Not found', 'code': 404}, 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Internal server error: {e}")
        if request.path.startswith('/api/'):
            return {'error': 'Internal server error', 'code': 500}, 500
        return render_template('500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.getenv('PORT', 8790))
    app.run(host='0.0.0.0', port=port, debug=debug)
