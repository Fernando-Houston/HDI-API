import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application configuration settings"""
    
    # Perplexity API
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    PERPLEXITY_MODEL: str = os.getenv("PERPLEXITY_MODEL", "sonar")  # IMPORTANT: sonar, not sonar-pro
    PERPLEXITY_BASE_URL: str = "https://api.perplexity.ai"
    
    # Deployment
    DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "INTERNAL")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Flask
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "5000"))
    API_VERSION: str = os.getenv("API_VERSION", "v1")
    
    # Cache
    USE_CACHE: bool = os.getenv("USE_CACHE", "true").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "7200"))  # 120 * 60
    
    # HCAD Configuration
    HCAD_BASE_URL: str = os.getenv("HCAD_BASE_URL", "https://public.hcad.org")
    HCAD_CACHE_TTL: int = int(os.getenv("HCAD_CACHE_TTL", "86400"))  # 24 hours
    
    # Cost Tracking
    COST_PER_QUERY_THRESHOLD: float = float(os.getenv("COST_PER_QUERY_THRESHOLD", "0.004"))
    PERPLEXITY_COST_PER_1000: float = float(os.getenv("PERPLEXITY_COST_PER_1000", "6"))
    
    # Security
    API_KEY_REQUIRED: bool = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    # Monitoring
    ENABLE_MONITORING: bool = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    
    # Data Sources
    CENSUS_API_KEY: Optional[str] = os.getenv("CENSUS_API_KEY") or None
    NOAA_API_KEY: Optional[str] = os.getenv("NOAA_API_KEY") or None
    
    @classmethod
    def validate(cls) -> None:
        """Validate required settings"""
        if not cls.PERPLEXITY_API_KEY:
            raise ValueError("PERPLEXITY_API_KEY is required")
        
        if cls.PERPLEXITY_MODEL not in ["sonar", "sonar-reasoning"]:
            raise ValueError(f"Invalid PERPLEXITY_MODEL: {cls.PERPLEXITY_MODEL}")
        
        if cls.DEPLOYMENT_MODE not in ["INTERNAL", "PRODUCTION"]:
            raise ValueError(f"Invalid DEPLOYMENT_MODE: {cls.DEPLOYMENT_MODE}")

# Create singleton instance
settings = Settings()