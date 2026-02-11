"""
IP Checker Application Package
Application Factory Pattern Implementation
"""

from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

from .config import config_by_name
from .extensions import limiter, talisman


def create_app(config_name='development'):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    limiter.init_app(app)
    talisman.init_app(app, force_https=app.config.get('FORCE_HTTPS', False))
    
    # Register blueprints
    from .api.geolocation import geo_bp
    from .api.network import net_bp
    from .api.security import sec_bp
    from .api.reports import report_bp
    
    app.register_blueprint(geo_bp, url_prefix='/api')
    app.register_blueprint(net_bp, url_prefix='/api')
    app.register_blueprint(sec_bp, url_prefix='/api')
    app.register_blueprint(report_bp, url_prefix='/api')
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_error_handlers(app):
    """Register global error handlers."""
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate limit exceeded", "success": False}), 429
    
    @app.errorhandler(404)
    def not_found_handler(e):
        return jsonify({"error": "Endpoint not found", "success": False}), 404
    
    @app.errorhandler(500)
    def internal_error_handler(e):
        # Log the error (assuming logger is configured)
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Internal error: {e}")
        except:
            pass
        return jsonify({"error": "Internal server error", "success": False}), 500