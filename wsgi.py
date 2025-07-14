#!/usr/bin/env python3
"""Simple WSGI entry point for Railway"""

import os
import sys

# Debug: Print environment info
print(f"Working directory: {os.getcwd()}")
print(f"Files in /app: {os.listdir('/app') if os.path.exists('/app') else 'N/A'}")
print(f"Files in current dir: {os.listdir('.')}")

# Set up Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Debug: Check if backend directory exists
backend_path = os.path.join(current_dir, 'backend')
print(f"Backend path exists: {os.path.exists(backend_path)}")
if os.path.exists(backend_path):
    print(f"Files in backend: {os.listdir(backend_path)}")
    services_path = os.path.join(backend_path, 'services')
    if os.path.exists(services_path):
        print(f"Files in services: {os.listdir(services_path)}")

# Import the app
try:
    from backend.app import create_app
    app = create_app()
    print("✓ Successfully imported and created HDI app")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print(f"Python path: {sys.path[:5]}")
    
    # Fallback to basic Flask app
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    def health():
        return jsonify({
            "status": "error", 
            "message": f"HDI API import failed: {e}",
            "debug": {
                "working_dir": os.getcwd(),
                "backend_exists": os.path.exists(backend_path),
                "python_path": sys.path[:3]
            }
        })
    
    @app.route('/health')
    def health_check():
        return jsonify({"status": "fallback_mode"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)