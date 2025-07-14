#!/usr/bin/env python3
"""Railway startup script for HDI Platform"""

import os
from backend.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)