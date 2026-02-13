"""
IP Checker Pro - Optimized Entry Point
======================================

This is the main entry point for the optimized IP Checker application.

Usage:
    python run.py
    
    # Or with environment variables:
    FLASK_DEBUG=true LOCAL_ONLY=false python run.py

Environment Variables:
    - SECRET_KEY: Flask secret key
    - LOCAL_ONLY: Restrict to local access (default: true)
    - FLASK_DEBUG: Enable debug mode (default: false)
    - FLASK_HOST: Server host (default: 127.0.0.1)
    - FLASK_PORT: Server port (default: 5000)
    - GEO_CACHE_TTL: Cache TTL in seconds (default: 3600)
    - GEO_LOOKUP_LIMIT: Max geo lookups per scan (default: 50)
    - RATE_LIMIT_DEFAULT: Rate limit string (default: "200 per day,50 per hour")
    - LOG_LEVEL: Logging level (default: INFO)
    - ENABLE_METRICS: Enable metrics collection (default: true)
"""

import os
import sys

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ip_checker import create_app, __version__, get_config


def print_banner(config):
    """Print startup banner."""
    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🛡️  IP Checker Pro v{__version__:<40}║
║                                                                  ║
║   Optimized Network Intelligence Platform                        ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║   Debug Mode:    {str(config.FLASK_DEBUG):<49}║
║   Host:          {config.FLASK_HOST:<49}║
║   Port:          {config.FLASK_PORT:<49}║
║   Local Only:    {str(config.LOCAL_ONLY):<49}║
║   Cache Type:    {config.CACHE_TYPE:<49}║
║   Rate Limit:    {config.RATE_LIMIT_DEFAULT:<49}║
╚══════════════════════════════════════════════════════════════════╝

Server starting at http://{config.FLASK_HOST}:{config.FLASK_PORT}/
Press Ctrl+C to stop
    """
    print(banner)


def main():
    """Main entry point."""
    try:
        # Get configuration
        config = get_config()
        
        # Print startup banner
        print_banner(config)
        
        # Create and run app
        app = create_app()
        
        app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG,
            threaded=True,
            use_reloader=config.FLASK_DEBUG,
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
