"""
Flask Application Factory
Optimized for performance with proper initialization patterns.
"""

import logging
import os
from typing import Optional

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

from ip_checker.core.config import config


def setup_logging() -> logging.Logger:
    """Configure optimized logging."""
    logger = logging.getLogger('ip_checker')
    
    if logger.handlers:
        return logger
    
    log_level = logging.DEBUG if os.environ.get('FLASK_DEBUG') == 'true' else logging.INFO
    logger.setLevel(log_level)
    
    # Console handler with optimized formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # File handler for persistence
    file_handler = logging.FileHandler('app.log', mode='a')
    file_handler.setLevel(logging.INFO)
    
    # Efficient formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def create_app(test_config: Optional[dict] = None) -> Flask:
    """Application factory pattern for better testability and configuration."""
    
    app = Flask(__name__, 
                static_folder='../../static',
                template_folder='../../templates')
    
    # Load configuration
    app.config.from_mapping(
        SECRET_KEY=config.SECRET_KEY,
        JSON_SORT_KEYS=config.JSON_SORT_KEYS,
        VERSION=config.VERSION,
    )
    
    if test_config:
        app.config.from_mapping(test_config)
    
    # Setup logging
    logger = setup_logging()
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)
    
    # Security headers with optimized CSP
    Talisman(
        app,
        force_https=config.FORCE_HTTPS,
        content_security_policy={
            'default-src': "'self'",
            'script-src': [
                "'self'", "'unsafe-inline'",
                "https://cdn.jsdelivr.net", "https://unpkg.com",
                "https://cdnjs.cloudflare.com"
            ],
            'style-src': [
                "'self'", "'unsafe-inline'",
                "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com"
            ],
            'font-src': [
                "'self'", "https://fonts.gstatic.com",
                "https://cdnjs.cloudflare.com"
            ],
            'img-src': [
                "'self'", "data:",
                "https://*.tile.openstreetmap.org", "https://unpkg.com"
            ],
            'connect-src': "'self'",
        },
        content_security_policy_nonce_in=['script-src']
    )
    
    # Rate limiting
    Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=config.DEFAULT_RATE_LIMITS,
        storage_uri=config.RATE_LIMIT_STORAGE,
        strategy="fixed-window-elastic-expiry"
    )
    
    # Register blueprints
    from ip_checker.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Main routes
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        return jsonify({"error": "Not found", "success": False}), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify
        app.logger.warning(f"Rate limit exceeded")
        return jsonify({"error": "Rate limit exceeded", "success": False}), 429
    
    @app.errorhandler(500)
    def server_error(e):
        from flask import jsonify
        app.logger.error(f"Server error: {e}")
        return jsonify({"error": "Internal server error", "success": False}), 500
    
    app.logger.info(f"IP Checker Pro v{config.VERSION} initialized")
    return app
