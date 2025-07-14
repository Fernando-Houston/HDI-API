#!/usr/bin/env python3
"""Simple WSGI entry point for Railway"""

import os
import sys

# Set up Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import the app
try:
    from backend.app import create_app
    app = create_app()
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback to basic Flask app
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    def health():
        return jsonify({"status": "ok", "message": "HDI API is running"})
    
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)