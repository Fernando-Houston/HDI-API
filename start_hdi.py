#!/usr/bin/env python3
"""HDI Platform Launcher - Start API and Dashboard"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

def start_api():
    """Start the Flask API server"""
    print("🚀 Starting HDI API server...")
    return subprocess.Popen([
        sys.executable, "-m", "backend.app"
    ], cwd=Path(__file__).parent)

def start_dashboard():
    """Start the Streamlit dashboard"""
    print("🎨 Starting HDI Dashboard...")
    dashboard_script = Path(__file__).parent / "frontend" / "run_dashboard.py"
    return subprocess.Popen([
        sys.executable, str(dashboard_script)
    ], cwd=Path(__file__).parent)

def check_api_health():
    """Check if API is responding"""
    import requests
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Launch HDI platform"""
    print("🏠 HDI Platform Launcher")
    print("=" * 40)
    
    # Start API
    api_process = start_api()
    
    # Wait for API to be ready
    print("⏳ Waiting for API to start...")
    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        if check_api_health():
            print("✅ API is ready!")
            break
        if i == 29:
            print("❌ API failed to start")
            api_process.terminate()
            return
    
    # Start dashboard
    dashboard_process = start_dashboard()
    
    print("\n🎯 HDI Platform is running!")
    print("📊 API: http://localhost:5000")
    print("📊 API Docs: http://localhost:5000/docs")
    print("🎨 Dashboard: http://localhost:8501")
    print("\n⚠️  Press Ctrl+C to stop all services")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if api_process.poll() is not None:
                print("❌ API process stopped unexpectedly")
                break
            
            if dashboard_process.poll() is not None:
                print("❌ Dashboard process stopped unexpectedly")
                break
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping HDI Platform...")
        
        # Terminate processes
        api_process.terminate()
        dashboard_process.terminate()
        
        # Wait for clean shutdown
        try:
            api_process.wait(timeout=5)
            dashboard_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
            dashboard_process.kill()
        
        print("👋 HDI Platform stopped")

if __name__ == "__main__":
    main()