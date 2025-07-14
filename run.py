#!/usr/bin/env python3
"""Run HDI Flask application"""

from backend.app import app
from backend.config.settings import settings

if __name__ == "__main__":
    # Validate settings
    try:
        settings.validate()
        print(f"✓ Settings validated")
        print(f"  - Model: {settings.PERPLEXITY_MODEL}")
        print(f"  - Mode: {settings.DEPLOYMENT_MODE}")
        print(f"  - Cache: {'Enabled' if settings.USE_CACHE else 'Disabled'}")
    except Exception as e:
        print(f"✗ Settings validation failed: {e}")
        exit(1)
    
    # Run app
    print(f"\n🚀 Starting HDI API on http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"📚 API Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs\n")
    
    app.run(
        host=settings.API_HOST,
        port=settings.API_PORT,
        debug=settings.DEBUG
    )