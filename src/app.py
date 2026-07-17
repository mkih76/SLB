import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, send_from_directory, abort, redirect, request

from src.config import Config
from src.api.utils import init_db
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
from src.api.ocr import ocr_bp


def create_app():
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')

    app.config.from_object(Config)

    # Register blueprints
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
    app.register_blueprint(ocr_bp)

    # Initialize database
    with app.app_context():
        init_db()

    # Page routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login():
        return render_template('login.html')

    @app.route('/register')
    def register():
        return render_template('register.html')

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

    @app.route('/phrases/study')
    def phrases_study():
        return render_template('phrases_study.html')

    @app.route('/phrases')
    def phrases_page():
        return render_template('phrases.html')

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
        from flask import request
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

    @app.route("/health")
    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "slb"}, 200

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.route('/favicon.ico')
    def favicon():
        """Inline SVG favicon (申 character) — avoids 404 in browsers and is theme-aware"""
        svg = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="12" fill="#1c1e54"/>'
            '<text x="32" y="44" font-family="serif" font-size="36" '
            'font-weight="700" text-anchor="middle" fill="#f5e9d4">申</text>'
            '</svg>'
        )
        from flask import Response
        return Response(svg, mimetype='image/svg+xml')

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('404.html'), 500

    @app.route('/community')
    def community():
        return render_template('community.html')

    @app.route('/profile')
    def profile():
        return render_template('profile.html')

    # Admin routes
    def _admin_guard():
        """Check admin auth for page routes (same logic as admin_required but for templates)"""
        from src.api.utils import _extract_user_from_token
        user, err = _extract_user_from_token()
        if not user or user.get('role') not in ('super_admin', 'admin', 'reviewer', 'operator'):
            return False
        return True

    @app.route('/admin')
    def admin_index():
        if not _admin_guard():
            return redirect('/login')
        return render_template('admin/dashboard.html')

    @app.route('/admin/login')
    def admin_login():
        return render_template('admin/login.html')

    @app.route('/admin/users')
    def admin_users():
        if not _admin_guard():
            return redirect('/login')
        return render_template('admin/users.html')

    @app.route('/admin/papers')
    def admin_papers():
        if not _admin_guard():
            return redirect('/login')
        return render_template('admin/papers.html')

    @app.route('/admin/phrases')
    def admin_phrases():
        if not _admin_guard():
            return redirect('/login')
        return render_template('admin/phrases.html')

    @app.route('/admin/reviews')
    def admin_reviews():
        if not _admin_guard():
            return redirect('/login')
        return render_template('admin/reviews.html')

    @app.route('/admin/stats')
    def admin_stats():
        if not _admin_guard():
            return redirect('/login')
        return render_template('admin/stats.html')

    @app.route('/admin/logs')
    def admin_logs():
        if not _admin_guard():
            return redirect('/login')
        return render_template('admin/logs.html')

    # Favicon — handled by SVG inline route above (avoid 404 + add brand mark)

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8790, debug=True)