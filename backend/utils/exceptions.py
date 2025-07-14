"""Custom exceptions for HDI platform"""

class HDIException(Exception):
    """Base exception for HDI platform"""
    pass

class PerplexityAPIError(HDIException):
    """Raised when Perplexity API fails"""
    pass

class RateLimitError(HDIException):
    """Raised when rate limit is exceeded"""
    pass

class HCADScrapingError(HDIException):
    """Raised when HCAD scraping fails"""
    pass

class CacheError(HDIException):
    """Raised when cache operations fail"""
    pass

class DataFusionError(HDIException):
    """Raised when data fusion fails"""
    pass

class ValidationError(HDIException):
    """Raised when input validation fails"""
    pass

class AuthenticationError(HDIException):
    """Raised when authentication fails"""
    pass

class ConfigurationError(HDIException):
    """Raised when configuration is invalid"""
    pass