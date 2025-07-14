"""Analytics and usage tracking endpoints"""

from flask import request, g
from flask_restx import Namespace, Resource, fields
from datetime import datetime, timedelta

from backend.monitoring.usage_tracker import usage_tracker
from backend.utils.exceptions import ValidationError

analytics_ns = Namespace("analytics", description="Usage analytics and insights")

# Response models
daily_stats_model = analytics_ns.model("DailyStats", {
    "total_queries": fields.Integer(description="Total queries for the day"),
    "successful_queries": fields.Integer(description="Successful queries"),
    "cache_hits": fields.Integer(description="Number of cache hits"),
    "cache_hit_rate": fields.Float(description="Cache hit rate (0-1)"),
    "total_cost": fields.Float(description="Total estimated cost"),
    "average_response_time": fields.Float(description="Average response time in seconds")
})

popular_query_model = analytics_ns.model("PopularQuery", {
    "query_type": fields.String(description="Type of query"),
    "count": fields.Integer(description="Number of times executed")
})

insight_model = analytics_ns.model("Insight", {
    "type": fields.String(description="Type of insight", enum=["performance", "usage", "cost", "reliability"]),
    "message": fields.String(description="Insight message"),
    "priority": fields.String(description="Priority level", enum=["high", "medium", "low", "info"])
})

insights_response_model = analytics_ns.model("InsightsResponse", {
    "generated_at": fields.String(description="Timestamp when insights were generated"),
    "insights": fields.List(fields.Nested(insight_model), description="List of insights")
})

cost_breakdown_item_model = analytics_ns.model("CostBreakdownItem", {
    "query_type": fields.String(description="Type of query"),
    "cost": fields.Float(description="Total cost for this query type"),
    "percentage": fields.Float(description="Percentage of total cost")
})

cost_breakdown_model = analytics_ns.model("CostBreakdown", {
    "period_days": fields.Integer(description="Number of days analyzed"),
    "total_cost": fields.Float(description="Total cost for the period"),
    "average_daily_cost": fields.Float(description="Average daily cost"),
    "breakdown": fields.List(fields.Nested(cost_breakdown_item_model), description="Cost breakdown by query type")
})

@analytics_ns.route("/stats/daily")
class DailyStats(Resource):
    """Daily usage statistics"""
    
    @analytics_ns.doc("get_daily_stats")
    @analytics_ns.param("date", "Date in YYYY-MM-DD format (default: today)")
    @analytics_ns.marshal_with(daily_stats_model)
    def get(self):
        """Get usage statistics for a specific day"""
        date_str = request.args.get("date")
        
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD")
        else:
            date = datetime.utcnow()
        
        stats = usage_tracker.get_daily_stats(date)
        
        # Calculate cache hit rate if not present
        if "cache_hit_rate" not in stats and stats.get("total_queries", 0) > 0:
            stats["cache_hit_rate"] = stats.get("cache_hits", 0) / stats["total_queries"]
        
        return stats

@analytics_ns.route("/stats/weekly")
class WeeklyStats(Resource):
    """Weekly usage statistics"""
    
    @analytics_ns.doc("get_weekly_stats")
    def get(self):
        """Get usage statistics for the past 7 days"""
        weekly_stats = {
            "period": "last_7_days",
            "daily_breakdown": [],
            "totals": {
                "total_queries": 0,
                "successful_queries": 0,
                "cache_hits": 0,
                "total_cost": 0.0
            }
        }
        
        for i in range(7):
            date = datetime.utcnow() - timedelta(days=i)
            daily = usage_tracker.get_daily_stats(date)
            
            if daily:
                weekly_stats["daily_breakdown"].append({
                    "date": date.strftime("%Y-%m-%d"),
                    "stats": daily
                })
                
                # Update totals
                weekly_stats["totals"]["total_queries"] += daily.get("total_queries", 0)
                weekly_stats["totals"]["successful_queries"] += daily.get("successful_queries", 0)
                weekly_stats["totals"]["cache_hits"] += daily.get("cache_hits", 0)
                weekly_stats["totals"]["total_cost"] += daily.get("total_cost", 0.0)
        
        # Calculate averages
        if weekly_stats["totals"]["total_queries"] > 0:
            weekly_stats["totals"]["success_rate"] = (
                weekly_stats["totals"]["successful_queries"] / 
                weekly_stats["totals"]["total_queries"]
            )
            weekly_stats["totals"]["cache_hit_rate"] = (
                weekly_stats["totals"]["cache_hits"] / 
                weekly_stats["totals"]["total_queries"]
            )
        
        return weekly_stats

@analytics_ns.route("/popular-queries")
class PopularQueries(Resource):
    """Most popular queries"""
    
    @analytics_ns.doc("get_popular_queries")
    @analytics_ns.param("days", "Number of days to look back (default: 7)")
    @analytics_ns.param("limit", "Maximum number of results (default: 10)")
    @analytics_ns.marshal_list_with(popular_query_model)
    def get(self):
        """Get most popular queries over a time period"""
        days = request.args.get("days", 7, type=int)
        limit = request.args.get("limit", 10, type=int)
        
        if days < 1 or days > 90:
            raise ValidationError("Days must be between 1 and 90")
        
        if limit < 1 or limit > 50:
            raise ValidationError("Limit must be between 1 and 50")
        
        return usage_tracker.get_popular_queries(days=days, limit=limit)

@analytics_ns.route("/insights")
class Insights(Resource):
    """Usage insights and recommendations"""
    
    @analytics_ns.doc("get_insights")
    @analytics_ns.marshal_with(insights_response_model)
    def get(self):
        """Get actionable insights from usage data"""
        return usage_tracker.generate_insights()

@analytics_ns.route("/cost-breakdown")
class CostBreakdown(Resource):
    """Cost analysis"""
    
    @analytics_ns.doc("get_cost_breakdown")
    @analytics_ns.param("days", "Number of days to analyze (default: 30)")
    @analytics_ns.marshal_with(cost_breakdown_model)
    def get(self):
        """Get cost breakdown by query type"""
        days = request.args.get("days", 30, type=int)
        
        if days < 1 or days > 365:
            raise ValidationError("Days must be between 1 and 365")
        
        return usage_tracker.get_cost_breakdown(days=days)

@analytics_ns.route("/user/<string:user_id>/stats")
class UserStats(Resource):
    """User-specific statistics"""
    
    @analytics_ns.doc("get_user_stats")
    @analytics_ns.param("month", "Month in YYYY-MM format (default: current month)")
    def get(self, user_id):
        """Get statistics for a specific user"""
        month = request.args.get("month")
        
        if month:
            try:
                # Validate month format
                datetime.strptime(month + "-01", "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Invalid month format. Use YYYY-MM")
        
        stats = usage_tracker.get_user_stats(user_id, month)
        
        if not stats:
            return {"message": f"No data found for user {user_id}"}, 404
        
        return {
            "user_id": user_id,
            "month": month or datetime.utcnow().strftime("%Y-%m"),
            "stats": stats
        }

@analytics_ns.route("/performance-metrics")
class PerformanceMetrics(Resource):
    """System performance metrics"""
    
    @analytics_ns.doc("get_performance_metrics")
    def get(self):
        """Get system performance metrics"""
        # Get today's stats
        today_stats = usage_tracker.get_daily_stats()
        
        # Calculate key metrics
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "response_time": {
                "average": today_stats.get("average_response_time", 0),
                "target": 3.0,
                "status": "healthy" if today_stats.get("average_response_time", 0) < 3.0 else "warning"
            },
            "cache_performance": {
                "hit_rate": today_stats.get("cache_hit_rate", 0),
                "target": 0.6,
                "status": "healthy" if today_stats.get("cache_hit_rate", 0) > 0.6 else "needs_improvement"
            },
            "reliability": {
                "success_rate": (
                    today_stats.get("successful_queries", 0) / today_stats.get("total_queries", 1)
                    if today_stats.get("total_queries", 0) > 0 else 0
                ),
                "target": 0.99,
                "status": "healthy" if today_stats.get("successful_queries", 0) / max(today_stats.get("total_queries", 1), 1) > 0.99 else "warning"
            },
            "cost_efficiency": {
                "average_cost_per_query": (
                    today_stats.get("total_cost", 0) / today_stats.get("total_queries", 1)
                    if today_stats.get("total_queries", 0) > 0 else 0
                ),
                "target": 0.004,
                "status": "healthy" if today_stats.get("total_cost", 0) / max(today_stats.get("total_queries", 1), 1) < 0.004 else "over_budget"
            }
        }
        
        return metrics