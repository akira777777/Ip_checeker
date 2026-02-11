"""
Main entry point for the IP Checker application.
Uses the application factory pattern.
"""

import os
import sys

# Add the parent directory to Python path to import the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ip_checker.app import create_app

# Create application instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == "__main__":
    # Create cache directory if it doesn't exist
    cache_dir = os.environ.get('CACHE_DIR', './cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    # Run the application
    app.run(
        debug=False, 
        host="127.0.0.1", 
        port=int(os.environ.get('PORT', 5000))
    )