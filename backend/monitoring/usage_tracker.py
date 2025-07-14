"""Usage analytics tracking for HDI platform"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import structlog
from flask import g, request
import redis
from dataclasses import dataclass, asdict

from backend.config.settings import settings

logger = structlog.get_logger(__name__)

@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query_type: str
    endpoint: str
    user: str
    response_time: float
    success: bool
    cache_hit: bool
    cost: float
    timestamp: datetime
    metadata: Dict[str, Any] = None

class UsageTracker:
    """Track and analyze platform usage"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize usage tracker
        
        Args:
            redis_client: Optional Redis client for persistence
        """
        self.redis_client = redis_client
        self.current_session_metrics = []
        
        # Try to connect to Redis if not provided
        if not self.redis_client and settings.USE_CACHE:
            try:
                self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
                self.redis_client.ping()
                logger.info("UsageTracker connected to Redis")
            except Exception as e:
                logger.warning("UsageTracker Redis connection failed", error=str(e))
                self.redis_client = None
    
    def track_query(
        self,
        query_type: str,
        endpoint: str,
        user: str,
        response_time: float,
        success: bool = True,
        cache_hit: bool = False,
        cost: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a query/request
        
        Args:
            query_type: Type of query (e.g., "property_search", "market_analysis")
            endpoint: API endpoint called
            user: User identifier (could be IP, API key, etc.)
            response_time: Time taken to process request (seconds)
            success: Whether request was successful
            cache_hit: Whether response was from cache
            cost: Estimated cost of the query
            metadata: Additional metadata
        """
        metric = QueryMetrics(
            query_type=query_type,
            endpoint=endpoint,
            user=user,
            response_time=response_time,
            success=success,
            cache_hit=cache_hit,
            cost=cost,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store in memory
        self.current_session_metrics.append(metric)
        
        # Store in Redis if available
        if self.redis_client:
            try:
                # Store in time-series format
                key = f"usage:{datetime.utcnow().strftime('%Y-%m-%d')}:{endpoint}"
                self.redis_client.lpush(key, json.dumps(asdict(metric), default=str))
                self.redis_client.expire(key, 86400 * 30)  # Keep for 30 days
                
                # Update counters
                self._update_counters(metric)
                
            except Exception as e:
                logger.error("Failed to store usage metric in Redis", error=str(e))
    
    def _update_counters(self, metric: QueryMetrics) -> None:
        """Update Redis counters for quick stats"""
        if not self.redis_client:
            return
        
        try:
            pipe = self.redis_client.pipeline()
            
            # Daily counters
            day_key = f"stats:{datetime.utcnow().strftime('%Y-%m-%d')}"
            pipe.hincrby(day_key, "total_queries", 1)
            pipe.hincrby(day_key, f"queries:{metric.query_type}", 1)
            pipe.hincrby(day_key, f"endpoint:{metric.endpoint}", 1)
            
            if metric.success:
                pipe.hincrby(day_key, "successful_queries", 1)
            
            if metric.cache_hit:
                pipe.hincrby(day_key, "cache_hits", 1)
            
            # Add to cost counter
            pipe.hincrbyfloat(day_key, "total_cost", metric.cost)
            
            # User stats
            user_key = f"user_stats:{metric.user}:{datetime.utcnow().strftime('%Y-%m')}"
            pipe.hincrby(user_key, "queries", 1)
            pipe.hincrbyfloat(user_key, "total_cost", metric.cost)
            
            pipe.execute()
            
        except Exception as e:
            logger.error("Failed to update counters", error=str(e))
    
    def get_daily_stats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get usage statistics for a specific day
        
        Args:
            date: Date to get stats for (default: today)
            
        Returns:
            Daily statistics
        """
        if not date:
            date = datetime.utcnow()
        
        day_key = f"stats:{date.strftime('%Y-%m-%d')}"
        
        if self.redis_client:
            try:
                stats = self.redis_client.hgetall(day_key)
                
                # Convert bytes to strings and numbers
                return {
                    k.decode(): float(v) if b'cost' in k or k == b'cache_hit_rate' else int(v)
                    for k, v in stats.items()
                }
            except Exception as e:
                logger.error("Failed to get daily stats", error=str(e))
        
        # Fallback to in-memory stats
        return self._calculate_memory_stats(date)
    
    def _calculate_memory_stats(self, date: datetime) -> Dict[str, Any]:
        """Calculate stats from in-memory metrics"""
        day_metrics = [
            m for m in self.current_session_metrics
            if m.timestamp.date() == date.date()
        ]
        
        if not day_metrics:
            return {}
        
        stats = {
            "total_queries": len(day_metrics),
            "successful_queries": sum(1 for m in day_metrics if m.success),
            "cache_hits": sum(1 for m in day_metrics if m.cache_hit),
            "total_cost": sum(m.cost for m in day_metrics),
            "average_response_time": sum(m.response_time for m in day_metrics) / len(day_metrics)
        }
        
        # Calculate cache hit rate
        if stats["total_queries"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_queries"]
        
        return stats
    
    def get_popular_queries(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular queries over a time period
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of popular queries with counts
        """
        query_counts = defaultdict(int)
        
        if self.redis_client:
            try:
                # Aggregate from Redis
                for i in range(days):
                    date = datetime.utcnow() - timedelta(days=i)
                    day_key = f"stats:{date.strftime('%Y-%m-%d')}"
                    
                    # Get all query type counters
                    stats = self.redis_client.hgetall(day_key)
                    for key, count in stats.items():
                        if key.startswith(b'queries:'):
                            query_type = key.decode().replace('queries:', '')
                            query_counts[query_type] += int(count)
                
            except Exception as e:
                logger.error("Failed to get popular queries from Redis", error=str(e))
        
        # Also check in-memory metrics
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        for metric in self.current_session_metrics:
            if metric.timestamp >= cutoff_date:
                query_counts[metric.query_type] += 1
        
        # Sort and return top queries
        sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"query_type": query_type, "count": count}
            for query_type, count in sorted_queries[:limit]
        ]
    
    def get_user_stats(self, user: str, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific user
        
        Args:
            user: User identifier
            month: Month in YYYY-MM format (default: current month)
            
        Returns:
            User statistics
        """
        if not month:
            month = datetime.utcnow().strftime('%Y-%m')
        
        user_key = f"user_stats:{user}:{month}"
        
        if self.redis_client:
            try:
                stats = self.redis_client.hgetall(user_key)
                return {
                    k.decode(): float(v) if k == b'total_cost' else int(v)
                    for k, v in stats.items()
                }
            except Exception as e:
                logger.error("Failed to get user stats", error=str(e))
        
        # Fallback to in-memory
        user_metrics = [
            m for m in self.current_session_metrics
            if m.user == user and m.timestamp.strftime('%Y-%m') == month
        ]
        
        if not user_metrics:
            return {}
        
        return {
            "queries": len(user_metrics),
            "total_cost": sum(m.cost for m in user_metrics),
            "average_response_time": sum(m.response_time for m in user_metrics) / len(user_metrics),
            "cache_hit_rate": sum(1 for m in user_metrics if m.cache_hit) / len(user_metrics)
        }
    
    def generate_insights(self) -> Dict[str, Any]:
        """
        Generate actionable insights from usage data
        
        Returns:
            Dictionary of insights
        """
        insights = {
            "generated_at": datetime.utcnow().isoformat(),
            "insights": []
        }
        
        # Get recent stats
        today_stats = self.get_daily_stats()
        popular_queries = self.get_popular_queries(days=7)
        
        # Insight 1: Cache effectiveness
        if today_stats.get("total_queries", 0) > 0:
            cache_hit_rate = today_stats.get("cache_hits", 0) / today_stats["total_queries"]
            if cache_hit_rate < 0.5:
                insights["insights"].append({
                    "type": "performance",
                    "message": f"Cache hit rate is only {cache_hit_rate:.1%}. Consider optimizing cache strategy.",
                    "priority": "high"
                })
            else:
                insights["insights"].append({
                    "type": "performance",
                    "message": f"Cache hit rate is {cache_hit_rate:.1%}, saving approximately ${today_stats.get('total_cost', 0) * cache_hit_rate:.2f} today.",
                    "priority": "info"
                })
        
        # Insight 2: Popular queries
        if popular_queries:
            top_query = popular_queries[0]
            insights["insights"].append({
                "type": "usage",
                "message": f"Most popular query type: '{top_query['query_type']}' with {top_query['count']} requests this week.",
                "priority": "info"
            })
        
        # Insight 3: Cost trends
        weekly_cost = sum(
            self.get_daily_stats(datetime.utcnow() - timedelta(days=i)).get("total_cost", 0)
            for i in range(7)
        )
        
        if weekly_cost > 0:
            insights["insights"].append({
                "type": "cost",
                "message": f"Total API costs this week: ${weekly_cost:.2f}",
                "priority": "info"
            })
        
        # Insight 4: Error rates
        if today_stats.get("total_queries", 0) > 0:
            success_rate = today_stats.get("successful_queries", 0) / today_stats["total_queries"]
            if success_rate < 0.95:
                insights["insights"].append({
                    "type": "reliability",
                    "message": f"Success rate is {success_rate:.1%}. Investigation recommended.",
                    "priority": "high"
                })
        
        return insights
    
    def get_cost_breakdown(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cost breakdown by query type
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Cost breakdown
        """
        costs_by_type = defaultdict(float)
        total_cost = 0.0
        
        # Aggregate from memory
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        for metric in self.current_session_metrics:
            if metric.timestamp >= cutoff_date:
                costs_by_type[metric.query_type] += metric.cost
                total_cost += metric.cost
        
        # Sort by cost
        sorted_costs = sorted(costs_by_type.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "period_days": days,
            "total_cost": total_cost,
            "average_daily_cost": total_cost / days if days > 0 else 0,
            "breakdown": [
                {
                    "query_type": query_type,
                    "cost": cost,
                    "percentage": (cost / total_cost * 100) if total_cost > 0 else 0
                }
                for query_type, cost in sorted_costs
            ]
        }

# Global instance
usage_tracker = UsageTracker()

# Flask integration helpers
def track_request():
    """Track Flask request (to be used as before_request handler)"""
    g.request_start_time = datetime.utcnow()

def track_response(response):
    """Track Flask response (to be used as after_request handler)"""
    if hasattr(g, 'request_start_time'):
        response_time = (datetime.utcnow() - g.request_start_time).total_seconds()
        
        # Determine query type from endpoint
        endpoint = request.endpoint or "unknown"
        query_type = endpoint.split('.')[-1] if endpoint else "unknown"
        
        # Get user identifier (IP address for now)
        user = request.remote_addr or "anonymous"
        
        # Check if response was from cache
        cache_hit = response.headers.get('X-Cache-Hit', 'false').lower() == 'true'
        
        # Estimate cost (this would be set by the actual endpoint)
        cost = g.get('query_cost', 0.0)
        
        # Track the request
        usage_tracker.track_query(
            query_type=query_type,
            endpoint=request.path,
            user=user,
            response_time=response_time,
            success=response.status_code < 400,
            cache_hit=cache_hit,
            cost=cost,
            metadata={
                "method": request.method,
                "status_code": response.status_code
            }
        )
    
    return response