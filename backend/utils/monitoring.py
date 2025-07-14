"""Performance monitoring for HDI platform"""

import time
import functools
from typing import Callable, Dict, Any, Optional, List
import structlog
from datetime import datetime
import threading
from collections import deque

logger = structlog.get_logger(__name__)

class PerformanceMonitor:
    """Track API performance and alert on slow responses"""
    
    def __init__(self, alert_threshold_seconds: float = 2.0):
        self.alert_threshold = alert_threshold_seconds
        self.metrics = {
            'total_requests': 0,
            'slow_requests': 0,
            'errors': 0,
            'total_response_time': 0.0
        }
        self.recent_requests = deque(maxlen=1000)  # Keep last 1000 requests
        self._lock = threading.Lock()
    
    def record_request(self, endpoint: str, method: str, 
                      response_time: float, status_code: int,
                      error: Optional[str] = None):
        """Record a request's performance metrics"""
        with self._lock:
            self.metrics['total_requests'] += 1
            self.metrics['total_response_time'] += response_time
            
            if response_time > self.alert_threshold:
                self.metrics['slow_requests'] += 1
                logger.warning("Slow request detected",
                             endpoint=endpoint,
                             method=method,
                             response_time=response_time,
                             threshold=self.alert_threshold)
            
            if status_code >= 500 or error:
                self.metrics['errors'] += 1
            
            # Record request details
            self.recent_requests.append({
                'timestamp': datetime.utcnow(),
                'endpoint': endpoint,
                'method': method,
                'response_time': response_time,
                'status_code': status_code,
                'error': error,
                'slow': response_time > self.alert_threshold
            })
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self._lock:
            total_requests = self.metrics['total_requests']
            if total_requests == 0:
                return {'status': 'no requests yet'}
            
            avg_response_time = self.metrics['total_response_time'] / total_requests
            slow_percentage = (self.metrics['slow_requests'] / total_requests) * 100
            error_rate = (self.metrics['errors'] / total_requests) * 100
            
            # Calculate recent trends (last 100 requests)
            recent = list(self.recent_requests)[-100:]
            recent_avg = sum(r['response_time'] for r in recent) / len(recent) if recent else 0
            recent_slow = sum(1 for r in recent if r['slow']) if recent else 0
            
            return {
                'total_requests': total_requests,
                'average_response_time': round(avg_response_time, 3),
                'slow_requests': self.metrics['slow_requests'],
                'slow_percentage': round(slow_percentage, 2),
                'error_rate': round(error_rate, 2),
                'recent_trend': {
                    'last_100_avg': round(recent_avg, 3),
                    'last_100_slow': recent_slow,
                    'improving': recent_avg < avg_response_time
                },
                'alert_threshold': self.alert_threshold,
                'health_status': self._calculate_health_status(slow_percentage, error_rate)
            }
    
    def get_slow_endpoints(self) -> List[Dict]:
        """Get endpoints that are consistently slow"""
        with self._lock:
            endpoint_stats = {}
            
            for req in self.recent_requests:
                endpoint = req['endpoint']
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {
                        'count': 0,
                        'total_time': 0,
                        'slow_count': 0
                    }
                
                endpoint_stats[endpoint]['count'] += 1
                endpoint_stats[endpoint]['total_time'] += req['response_time']
                if req['slow']:
                    endpoint_stats[endpoint]['slow_count'] += 1
            
            # Calculate averages and identify slow endpoints
            slow_endpoints = []
            for endpoint, stats in endpoint_stats.items():
                avg_time = stats['total_time'] / stats['count']
                if avg_time > self.alert_threshold * 0.8:  # 80% of threshold
                    slow_endpoints.append({
                        'endpoint': endpoint,
                        'average_time': round(avg_time, 3),
                        'request_count': stats['count'],
                        'slow_count': stats['slow_count'],
                        'slow_percentage': round((stats['slow_count'] / stats['count']) * 100, 2)
                    })
            
            return sorted(slow_endpoints, key=lambda x: x['average_time'], reverse=True)
    
    def _calculate_health_status(self, slow_percentage: float, error_rate: float) -> str:
        """Calculate overall health status"""
        if error_rate > 5 or slow_percentage > 20:
            return "unhealthy"
        elif error_rate > 2 or slow_percentage > 10:
            return "degraded"
        else:
            return "healthy"
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self.metrics = {
                'total_requests': 0,
                'slow_requests': 0,
                'errors': 0,
                'total_response_time': 0.0
            }
            self.recent_requests.clear()

# Global monitor instance
monitor = PerformanceMonitor(alert_threshold_seconds=2.0)

def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        error = None
        status_code = 200
        
        try:
            result = func(*args, **kwargs)
            
            # Extract status code if it's a tuple response
            if isinstance(result, tuple) and len(result) == 2:
                status_code = result[1]
            
            return result
            
        except Exception as e:
            error = str(e)
            status_code = 500
            raise
            
        finally:
            response_time = time.time() - start_time
            
            # Try to get endpoint name
            endpoint = func.__name__
            if hasattr(func, '__qualname__'):
                endpoint = func.__qualname__
            
            monitor.record_request(
                endpoint=endpoint,
                method='UNKNOWN',  # Would need request context for actual method
                response_time=response_time,
                status_code=status_code,
                error=error
            )
    
    return wrapper

# Middleware for Flask
def add_performance_monitoring(app):
    """Add performance monitoring middleware to Flask app"""
    from flask import request, g
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            
            monitor.record_request(
                endpoint=request.endpoint or request.path,
                method=request.method,
                response_time=response_time,
                status_code=response.status_code,
                error=None
            )
            
            # Add response time header
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
        
        return response
    
    @app.errorhandler(Exception)
    def handle_error(error):
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            
            monitor.record_request(
                endpoint=request.endpoint or request.path,
                method=request.method,
                response_time=response_time,
                status_code=500,
                error=str(error)
            )
        
        # Re-raise the error
        raise error

# API endpoint for metrics
def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive performance report"""
    return {
        'metrics': monitor.get_metrics(),
        'slow_endpoints': monitor.get_slow_endpoints(),
        'timestamp': datetime.utcnow().isoformat()
    }