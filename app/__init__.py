"""
Flask application factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # User loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.donor import donor as donor_bp
    app.register_blueprint(donor_bp, url_prefix='/donor')

    from app.requests_bp import requests as requests_bp
    app.register_blueprint(requests_bp, url_prefix='/requests')

    from app.admin import admin as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.api import api as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.main import main as main_bp
    app.register_blueprint(main_bp)

    # Context Processors for global metrics
    @app.context_processor
    def inject_metrics():
        from flask_login import current_user
        from app.models import Notification, BloodRequest
        metrics = {'unread': 0, 'active_request_count': 0}
        if current_user.is_authenticated:
            metrics['unread'] = Notification.query.filter_by(
                user_id=current_user.id, is_read=False).count()
            metrics['active_request_count'] = BloodRequest.query.filter_by(
                status='active').count()
        return metrics

    # Error handlers
    from app.errors import register_errors
    register_errors(app)

    # Start background scheduler
    from app.scheduler import start_scheduler
    start_scheduler(app)

    return app
