#!/usr/bin/env python3
"""HDI Streamlit Dashboard Runner"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    required = ['streamlit', 'requests', 'pandas', 'plotly']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Please install with: pip install -r frontend/requirements.txt")
        return False
    
    return True

def main():
    """Run the Streamlit dashboard"""
    print("🚀 Starting HDI Dashboard...")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Get the directory of this script
    current_dir = Path(__file__).parent
    app_path = current_dir / "streamlit_app.py"
    
    if not app_path.exists():
        print(f"❌ Streamlit app not found at {app_path}")
        sys.exit(1)
    
    # Run Streamlit
    try:
        print("🎯 Starting Streamlit server...")
        print("📊 Dashboard will be available at: http://localhost:8501")
        print("⚠️  Make sure the HDI API is running at http://localhost:5000")
        print()
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.serverAddress", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()