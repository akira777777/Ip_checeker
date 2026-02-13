"""
IP Checker Pro - Application Factory
====================================
Flask application factory with optimized configuration.
"""

import logging
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

try:
    from flask_talisman import Talisman
    TALISMAN_AVAILABLE = True
except ImportError:
    TALISMAN_AVAILABLE = False

from ip_checker.core.config import get_config
from ip_checker.api.routes import api

logger = logging.getLogger(__name__)


def setup_logging(config) -> logging.Logger:
    """Configure application logging."""
    # Create logs directory if needed
    if config.LOG_FILE:
        log_dir = Path(config.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if config.LOG_FILE:
        handlers.append(logging.FileHandler(config.LOG_FILE))
    
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format=config.LOG_FORMAT,
        handlers=handlers
    )
    
    return logging.getLogger('ip_checker')


def create_app(test_config: dict = None) -> Flask:
    """
    Application factory pattern.
    
    Args:
        test_config: Optional test configuration override
        
    Returns:
        Configured Flask application
    """
    # Get configuration
    config = get_config()
    
    # Override with test config if provided
    if test_config:
        for key, value in test_config.items():
            setattr(config, key, value)
    
    # Setup logging
    logger = setup_logging(config)
    logger.info(f"Starting IP Checker Pro v{config.version}")
    
    # Create Flask app
    app = Flask(
        __name__,
        template_folder='../../templates',
        static_folder='../../static'
    )
    
    # Configure app
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Optimize JSON responses
    
    # Setup security headers with Talisman
    if TALISMAN_AVAILABLE and not config.FLASK_DEBUG:
        Talisman(
            app,
            force_https=config.FORCE_HTTPS,
            content_security_policy=config.CSP,
            content_security_policy_nonce_in=['script-src'],
        )
        logger.info("Security headers enabled (Talisman)")
    
    # Setup rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=config.get_rate_limits(),
        storage_uri=config.RATE_LIMIT_STORAGE,
        strategy='fixed-window',
    )
    logger.info(f"Rate limiting enabled: {config.RATE_LIMIT_DEFAULT}")
    
    # Register blueprints
    app.register_blueprint(api)
    
    # Main routes
    @app.route('/')
    def index():
        """Serve main application."""
        return render_template('index.html')
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': str(error.description)
        }), 400
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': str(error.description)
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(429)
    def rate_limit_handler(error):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'message': str(error.description),
            'retry_after': error.description
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    # Request logging
    @app.before_request
    def log_request():
        from flask import request, g
        g.start_time = logging.time.time() if hasattr(logging, 'time') else __import__('time').time()
    
    @app.after_request
    def log_response(response):
        from flask import request, g
        
        duration = 0
        if hasattr(g, 'start_time'):
            duration = (__import__('time').time() - g.start_time) * 1000
        
        logger.debug(
            f"{request.method} {request.path} - {response.status_code} "
            f"({duration:.2f}ms)"
        )
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    # CLI commands
    @app.cli.command('clear-cache')
    def clear_cache():
        """Clear application cache."""
        from ip_checker.services.cache import get_cache
        cache = get_cache()
        cache.clear()
        print("Cache cleared successfully")
    
    @app.cli.command('status')
    def show_status():
        """Show application status."""
        print(f"\n{'='*50}")
        print(f"IP Checker Pro v{config.version}")
        print(f"{'='*50}")
        print(f"Debug Mode: {config.FLASK_DEBUG}")
        print(f"Local Only: {config.LOCAL_ONLY}")
        print(f"Rate Limit: {config.RATE_LIMIT_DEFAULT}")
        print(f"Cache TTL: {config.CACHE_TTL}s")
        print(f"{'='*50}\n")
    
    logger.info("Application initialized successfully")
    return app
