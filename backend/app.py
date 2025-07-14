"""HDI Flask Application"""

import os
import sys

# Add the project root to Python path for Railway
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, jsonify
from flask_restx import Api
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_compress import Compress
import structlog
from datetime import datetime

from backend.config.settings import settings
from backend.api.routes import register_routes
from backend.utils.exceptions import HDIException
from backend.utils.monitoring import add_performance_monitoring, get_performance_report

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

def create_app(config_name: str = "development") -> Flask:
    """Create and configure Flask application"""
    
    # Create Flask app
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG
    
    # Configure CORS with specific origins for your frontend
    CORS(app, 
         origins=[
             "https://hdi-grid-ui.vercel.app",  # Your Vercel frontend
             "http://localhost:5173",            # Vite development
             "http://localhost:3000",            # React development
             "http://localhost:4000",            # Alternative port
             "http://localhost:8501",            # Streamlit
         ],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         supports_credentials=True
    )
    
    # Configure Response Compression (70% size reduction)
    Compress(app)
    app.config['COMPRESS_ALGORITHM'] = 'gzip'
    app.config['COMPRESS_LEVEL'] = 6
    app.config['COMPRESS_MIN_SIZE'] = 500
    
    # Configure Rate Limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[
            f"{settings.RATE_LIMIT_PER_MINUTE} per minute",
            f"{settings.RATE_LIMIT_PER_HOUR} per hour"
        ],
        storage_uri=settings.REDIS_URL if settings.USE_CACHE else "memory://"
    )
    
    # Configure Caching
    cache_config = {
        "CACHE_TYPE": "RedisCache" if settings.USE_CACHE else "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": settings.CACHE_TTL
    }
    
    if settings.USE_CACHE:
        cache_config["CACHE_REDIS_URL"] = settings.REDIS_URL
    
    cache = Cache(app, config=cache_config)
    
    # Configure API
    api = Api(
        app,
        version="1.0",
        title="HDI - Houston Data Intelligence API",
        description="Real-time Houston real estate intelligence platform",
        doc="/docs" if settings.DEBUG else False,
        prefix=f"/api/{settings.API_VERSION}"
    )
    
    # Store extensions on app
    app.limiter = limiter
    app.cache = cache
    app.api = api
    
    # Register routes
    register_routes(api)
    
    # Add performance monitoring
    add_performance_monitoring(app)
    
    # Integrate usage tracking
    from backend.monitoring.usage_tracker import track_request, track_response
    app.before_request(track_request)
    app.after_request(track_response)
    
    # Performance metrics endpoint
    @app.route("/metrics/performance")
    def performance_metrics():
        """Get performance metrics"""
        return jsonify(get_performance_report())
    
    # Health check endpoint (outside API prefix)
    @app.route("/health", methods=["GET"])
    def health_check():
        """Basic health check endpoint"""
        from backend.services.perplexity_client import PerplexityClient
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.API_VERSION,
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "services": {}
        }
        
        # Check Perplexity API
        try:
            client = PerplexityClient()
            perplexity_healthy = client.health_check()
            health_status["services"]["perplexity"] = {
                "status": "healthy" if perplexity_healthy else "unhealthy",
                "model": settings.PERPLEXITY_MODEL
            }
        except Exception as e:
            health_status["services"]["perplexity"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check Redis if caching enabled
        if settings.USE_CACHE:
            try:
                cache.get("health_check_test")
                cache.set("health_check_test", "ok", timeout=10)
                health_status["services"]["redis"] = {"status": "healthy"}
            except Exception as e:
                health_status["services"]["redis"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code
    
    # Error handlers
    @app.errorhandler(HDIException)
    def handle_hdi_exception(error):
        """Handle custom HDI exceptions"""
        logger.error("HDI Exception", error=str(error), type=type(error).__name__)
        return jsonify({
            "error": type(error).__name__,
            "message": str(error)
        }), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        return jsonify({
            "error": "NotFound",
            "message": "The requested resource was not found"
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors"""
        logger.error("Internal server error", error=str(error))
        return jsonify({
            "error": "InternalServerError",
            "message": "An internal server error occurred"
        }), 500
    
    # Add welcome page
    @app.route('/')
    def welcome():
        """Welcome page with API documentation"""
        return jsonify({
            "message": "Welcome to HDI (Houston Data Intelligence) API",
            "version": "1.0",
            "status": "operational",
            "documentation": f"/docs" if settings.DEBUG else "Contact admin for API docs",
            "health_check": "/health",
            "endpoints": {
                "property_search": {
                    "method": "POST",
                    "url": "/api/v1/properties/search",
                    "description": "Search for property data by address",
                    "example_body": {"address": "1234 Main St, Houston, TX"}
                },
                "market_trends": {
                    "method": "GET", 
                    "url": "/api/v1/market/trends?area=Houston",
                    "description": "Get market trends for an area"
                },
                "batch_analysis": {
                    "method": "POST",
                    "url": "/api/v1/batch/analyze",
                    "description": "Analyze multiple properties (up to 100)"
                },
                "property_by_account": {
                    "method": "GET",
                    "url": "/api/v1/properties/account/{account_number}",
                    "description": "Get property by HCAD account number"
                }
            },
            "example_usage": {
                "curl": "curl -X POST https://hdi-api-production.up.railway.app/api/v1/properties/search -H 'Content-Type: application/json' -d '{\"address\": \"1234 Main St, Houston, TX\"}'",
                "note": "Most endpoints require POST method with JSON body"
            }
        })
    
    # Log app startup
    logger.info(
        "HDI Flask app created",
        debug=settings.DEBUG,
        deployment_mode=settings.DEPLOYMENT_MODE,
        cache_enabled=settings.USE_CACHE,
        rate_limiting_enabled=True
    )
    
    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    # Validate settings
    settings.validate()
    
    # Run development server
    app.run(
        host=settings.API_HOST,
        port=settings.API_PORT,
        debug=settings.DEBUG
    )