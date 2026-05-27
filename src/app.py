import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, send_from_directory

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

    # Initialize database
    with app.app_context():
        init_db()

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

    # Admin routes
    @app.route('/admin')
    def admin_index():
        return render_template('admin/dashboard.html')

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

    # Favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8790, debug=True)