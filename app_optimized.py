"""
IP Checker Pro - Optimized Entry Point
========================================

This is the optimized version of the IP Checker application with:
- Modular package structure for better maintainability
- Performance optimizations (caching, connection pooling)
- Enhanced security with proper validation
- Improved error handling and logging
- Better resource management

Usage:
    python app_optimized.py
    
Environment Variables:
    - SECRET_KEY: Flask secret key (auto-generated if not set)
    - LOCAL_ONLY: Restrict to local access (default: true)
    - FLASK_DEBUG: Enable debug mode (default: false)
    - FLASK_HOST: Server host (default: 127.0.0.1)
    - FLASK_PORT: Server port (default: 5000)
    - GEO_CACHE_TTL: Cache TTL in seconds (default: 3600)
    - GEO_LOOKUP_LIMIT: Max geo lookups per scan (default: 15)
"""

import os
import sys

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ip_checker import create_app, __version__


def main():
    """Main entry point with configuration."""
    
    # Configuration from environment
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    local_only = os.environ.get('LOCAL_ONLY', 'true').lower() == 'true'
    
    # Create app
    app = create_app()
    
    # Print startup info
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🛡️  IP Checker Pro v{__version__}                           ║
║                                                              ║
║   Optimized Network Intelligence Platform                    ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║   Debug Mode:    {str(debug_mode):<45}║
║   Host:          {host:<45}║
║   Port:          {port:<45}║
║   Local Only:    {str(local_only):<45}║
║   Version:       {__version__:<45}║
╚══════════════════════════════════════════════════════════════╝

Server starting at http://{host}:{port}/
Press Ctrl+C to stop
    """)
    
    try:
        app.run(
            debug=debug_mode,
            host=host,
            port=port,
            threaded=True,  # Enable threading for better performance
            use_reloader=debug_mode,  # Auto-reload only in debug mode
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
