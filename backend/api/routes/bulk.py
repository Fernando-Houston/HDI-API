"""Bulk property analysis endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields
import asyncio

from backend.services.bulk_analyzer import BulkAnalyzer
from backend.utils.exceptions import ValidationError

bulk_ns = Namespace("bulk", description="Bulk property operations")

# Request/Response models
bulk_analysis_request = bulk_ns.model("BulkAnalysisRequest", {
    "addresses": fields.List(
        fields.String,
        required=True,
        description="List of property addresses to analyze",
        min_items=1,
        max_items=50
    ),
    "analysis_type": fields.String(
        default="standard",
        enum=["standard", "quick", "investment"],
        description="Type of analysis to perform"
    ),
    "include_comparisons": fields.Boolean(
        default=True,
        description="Include comparative analysis between properties"
    )
})

property_result_model = bulk_ns.model("PropertyResult", {
    "address": fields.String(description="Property address"),
    "success": fields.Boolean(description="Analysis success status"),
    "data": fields.Raw(description="Property analysis data"),
    "error": fields.String(description="Error message if failed")
})

comparison_model = bulk_ns.model("Comparison", {
    "property_count": fields.Integer(description="Number of properties compared"),
    "comparison_matrix": fields.List(fields.Raw, description="Pairwise comparisons"),
    "key_differences": fields.List(fields.String, description="Key differences identified")
})

ranking_model = bulk_ns.model("Ranking", {
    "criteria": fields.String(description="Ranking criteria"),
    "ranked_properties": fields.List(fields.Raw, description="Properties in ranked order")
})

opportunity_model = bulk_ns.model("Opportunity", {
    "type": fields.String(description="Type of opportunity"),
    "address": fields.String(description="Property address"),
    "reason": fields.String(description="Reason for opportunity"),
    "confidence": fields.Float(description="Confidence score")
})

bulk_analysis_response = bulk_ns.model("BulkAnalysisResponse", {
    "summary": fields.Raw(description="Executive summary of analysis"),
    "properties": fields.List(fields.Nested(property_result_model), description="Individual property results"),
    "comparison": fields.Nested(comparison_model, description="Comparative analysis"),
    "rankings": fields.List(fields.Nested(ranking_model), description="Property rankings"),
    "opportunities": fields.List(fields.Nested(opportunity_model), description="Identified opportunities"),
    "market_context": fields.Raw(description="Overall market context"),
    "analysis_type": fields.String(description="Type of analysis performed"),
    "total_properties": fields.Integer(description="Total properties analyzed"),
    "successful_analyses": fields.Integer(description="Number of successful analyses"),
    "processing_time": fields.Float(description="Total processing time in seconds"),
    "timestamp": fields.String(description="Analysis timestamp")
})

@bulk_ns.route("/analyze")
class BulkPropertyAnalysis(Resource):
    """Bulk property analysis endpoint"""
    
    @bulk_ns.doc("bulk_analyze_properties")
    @bulk_ns.expect(bulk_analysis_request)
    @bulk_ns.marshal_with(bulk_analysis_response)
    def post(self):
        """Analyze multiple properties in bulk"""
        data = request.get_json()
        
        # Validate request
        if not data or "addresses" not in data:
            raise ValidationError("Addresses list is required")
        
        addresses = data["addresses"]
        if not addresses:
            raise ValidationError("At least one address is required")
        
        if len(addresses) > 50:
            raise ValidationError("Maximum 50 properties per bulk analysis")
        
        # Get analysis parameters
        analysis_type = data.get("analysis_type", "standard")
        include_comparisons = data.get("include_comparisons", True)
        
        # Initialize bulk analyzer
        analyzer = BulkAnalyzer()
        
        # Run async analysis in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                analyzer.analyze_properties(
                    addresses=addresses,
                    analysis_type=analysis_type,
                    include_comparisons=include_comparisons
                )
            )
            
            return results
            
        finally:
            loop.close()

@bulk_ns.route("/compare")
class BulkComparison(Resource):
    """Quick comparison of multiple properties"""
    
    @bulk_ns.doc("compare_properties")
    @bulk_ns.param("addresses", "Comma-separated list of addresses", required=True)
    def get(self):
        """Quick comparison of 2-5 properties"""
        addresses_param = request.args.get("addresses")
        
        if not addresses_param:
            raise ValidationError("Addresses parameter is required")
        
        # Parse addresses
        addresses = [addr.strip() for addr in addresses_param.split(",")]
        
        if len(addresses) < 2:
            raise ValidationError("At least 2 addresses required for comparison")
        
        if len(addresses) > 5:
            raise ValidationError("Maximum 5 properties for quick comparison")
        
        # Use bulk analyzer with quick analysis
        analyzer = BulkAnalyzer()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                analyzer.analyze_properties(
                    addresses=addresses,
                    analysis_type="quick",
                    include_comparisons=True
                )
            )
            
            # Return simplified comparison results
            return {
                "addresses": addresses,
                "comparison": results.get("comparison"),
                "rankings": results.get("rankings"),
                "summary": results.get("summary"),
                "timestamp": results.get("timestamp")
            }
            
        finally:
            loop.close()

@bulk_ns.route("/portfolio-analysis")
class PortfolioAnalysis(Resource):
    """Portfolio-level analysis"""
    
    @bulk_ns.doc("analyze_portfolio")
    @bulk_ns.expect(bulk_analysis_request)
    def post(self):
        """Analyze a portfolio of properties with investment focus"""
        data = request.get_json()
        
        if not data or "addresses" not in data:
            raise ValidationError("Addresses list is required")
        
        addresses = data["addresses"]
        
        # Force investment analysis type for portfolio
        analyzer = BulkAnalyzer()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                analyzer.analyze_properties(
                    addresses=addresses,
                    analysis_type="investment",
                    include_comparisons=True
                )
            )
            
            # Add portfolio-specific metrics
            portfolio_metrics = self._calculate_portfolio_metrics(results)
            results["portfolio_metrics"] = portfolio_metrics
            
            return results
            
        finally:
            loop.close()
    
    def _calculate_portfolio_metrics(self, results: dict) -> dict:
        """Calculate portfolio-level metrics"""
        successful = [
            p for p in results.get("properties", [])
            if p.get("success", False)
        ]
        
        if not successful:
            return {"error": "No successful analyses"}
        
        # Calculate portfolio metrics
        total_value = 0
        investment_scores = []
        
        for prop in successful:
            # Extract value
            value = self._extract_value(prop)
            if value:
                total_value += value
            
            # Extract investment score
            score = prop.get("data", {}).get("investment_score", 0)
            if score:
                investment_scores.append(score)
        
        metrics = {
            "total_portfolio_value": total_value,
            "property_count": len(successful),
            "average_property_value": total_value / len(successful) if successful else 0
        }
        
        if investment_scores:
            metrics["average_investment_score"] = sum(investment_scores) / len(investment_scores)
            metrics["highest_score"] = max(investment_scores)
            metrics["lowest_score"] = min(investment_scores)
        
        return metrics
    
    def _extract_value(self, property_result: dict) -> float:
        """Extract numeric value from property result"""
        try:
            value_str = property_result.get("data", {}).get("official_data", {}).get("appraised_value", "")
            if value_str:
                return float(str(value_str).replace("$", "").replace(",", ""))
        except:
            pass
        
        return 0