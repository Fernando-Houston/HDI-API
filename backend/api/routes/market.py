"""Market data endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields
from datetime import datetime

from backend.services.perplexity_client import PerplexityClient
from backend.utils.exceptions import ValidationError

market_ns = Namespace("market", description="Market data operations")

# Response models
market_response_model = market_ns.model("MarketResponse", {
    "data": fields.Raw(description="Market data", required=True),
    "metadata": fields.Raw(description="Response metadata", required=True),
    "success": fields.Boolean(description="Success status", required=True)
})

@market_ns.route("/trends")
class MarketTrends(Resource):
    """Market trends endpoint"""
    
    @market_ns.doc("get_market_trends")
    @market_ns.param("area", "Houston area/neighborhood name", required=True)
    @market_ns.marshal_with(market_response_model)
    def get(self):
        """Get current market trends for a Houston area"""
        area = request.args.get("area")
        
        if not area:
            raise ValidationError("Area parameter is required")
        
        # Initialize Perplexity client
        client = PerplexityClient()
        
        # Query for market trends
        response = client.query_with_template(
            "market_overview",
            area=area,
            date=datetime.now().strftime("%B %Y")
        )
        
        return response

@market_ns.route("/analysis")
class MarketAnalysis(Resource):
    """Market analysis endpoint"""
    
    @market_ns.doc("get_market_analysis")
    @market_ns.param("area", "Houston area/neighborhood name", required=True)
    @market_ns.param("timeframe", "Analysis timeframe (e.g., '90 days', '1 year')")
    @market_ns.marshal_with(market_response_model)
    def get(self):
        """Get detailed market analysis for a Houston area"""
        area = request.args.get("area")
        timeframe = request.args.get("timeframe", "90 days")
        
        if not area:
            raise ValidationError("Area parameter is required")
        
        # Initialize Perplexity client
        client = PerplexityClient()
        
        # Create custom query
        prompt = f"""
        Provide a detailed real estate market analysis for {area}, Houston, TX 
        over the last {timeframe}. Include:
        - Price trends and statistics
        - Inventory changes
        - Market velocity (days on market)
        - Key market drivers
        - Comparison to Houston overall
        
        Use current data and cite sources.
        """
        
        response = client.query(prompt)
        return response

@market_ns.route("/forecast")
class MarketForecast(Resource):
    """Market forecast endpoint"""
    
    @market_ns.doc("get_market_forecast")
    @market_ns.param("area", "Houston area/neighborhood name", required=True)
    @market_ns.param("timeframe", "Forecast timeframe (e.g., '6 months', '1 year')")
    @market_ns.marshal_with(market_response_model)
    def get(self):
        """Get market forecast for a Houston area"""
        area = request.args.get("area")
        timeframe = request.args.get("timeframe", "6 months")
        
        if not area:
            raise ValidationError("Area parameter is required")
        
        # Initialize Perplexity client
        client = PerplexityClient()
        
        # Query for market forecast
        response = client.query_with_template(
            "market_forecast",
            area=area,
            timeframe=timeframe
        )
        
        return response