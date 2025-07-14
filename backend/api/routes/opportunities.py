"""Opportunity finding and smart search endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields

from backend.services.smart_search import SmartSearchEngine, SearchCriteria
from backend.utils.exceptions import ValidationError

opportunities_ns = Namespace("opportunities", description="Smart property opportunity search")

# Request/Response models
search_criteria_model = opportunities_ns.model("SearchCriteria", {
    # Price criteria
    "min_price": fields.Float(description="Minimum price"),
    "max_price": fields.Float(description="Maximum price"),
    
    # Investment criteria
    "min_cap_rate": fields.Float(description="Minimum cap rate percentage"),
    "max_price_per_sqft": fields.Float(description="Maximum price per square foot"),
    
    # Location criteria
    "neighborhoods": fields.List(fields.String, description="List of neighborhoods"),
    "zip_codes": fields.List(fields.String, description="List of zip codes"),
    "school_districts": fields.List(fields.String, description="List of school districts"),
    
    # Property criteria
    "property_types": fields.List(fields.String, description="Property types (e.g., single-family, condo, multi-family)"),
    "property_type": fields.String(description="Single property type (alternative to property_types)"),
    "min_bedrooms": fields.Integer(description="Minimum number of bedrooms"),
    "min_bathrooms": fields.Float(description="Minimum number of bathrooms"),
    "min_sqft": fields.Integer(description="Minimum square footage"),
    "max_sqft": fields.Integer(description="Maximum square footage"),
    "min_lot_size": fields.Integer(description="Minimum lot size in sqft"),
    "year_built_after": fields.Integer(description="Year built after"),
    
    # Special criteria
    "distressed": fields.Boolean(description="Include distressed properties"),
    "pre_foreclosure": fields.Boolean(description="Include pre-foreclosure properties"),
    "new_construction": fields.Boolean(description="Only new construction"),
    "pool": fields.Boolean(description="Must have pool"),
    "garage": fields.Boolean(description="Must have garage"),
    
    # Investment specific
    "rental_ready": fields.Boolean(description="Ready for rental"),
    "fix_and_flip": fields.Boolean(description="Good for fix and flip"),
    "multi_family": fields.Boolean(description="Multi-family properties only")
})

opportunity_search_request = opportunities_ns.model("OpportunitySearchRequest", {
    "criteria": fields.Nested(search_criteria_model, required=True, description="Search criteria"),
    "limit": fields.Integer(default=20, description="Maximum results to return"),
    "sort_by": fields.String(
        default="value",
        enum=["value", "price", "score", "potential"],
        description="Sort results by"
    )
})

opportunity_model = opportunities_ns.model("Opportunity", {
    "address": fields.String(description="Property address or area"),
    "estimated_price": fields.Float(description="Estimated price"),
    "bedrooms": fields.Integer(description="Number of bedrooms"),
    "bathrooms": fields.Float(description="Number of bathrooms"),
    "sqft": fields.Integer(description="Square footage"),
    "description": fields.String(description="Property description"),
    "match_score": fields.Float(description="How well it matches criteria (0-10)"),
    "match_reasons": fields.List(fields.String, description="Reasons why it's a good match"),
    "source": fields.String(description="Data source")
})

search_summary_model = opportunities_ns.model("SearchSummary", {
    "total_opportunities": fields.Integer(description="Total opportunities found"),
    "average_match_score": fields.Float(description="Average match score"),
    "price_range": fields.Raw(description="Price range of results"),
    "neighborhoods": fields.Raw(description="Neighborhood distribution"),
    "top_reasons": fields.List(fields.Raw, description="Most common match reasons")
})

opportunity_search_response = opportunities_ns.model("OpportunitySearchResponse", {
    "criteria": fields.Raw(description="Search criteria used"),
    "opportunities": fields.List(fields.Nested(opportunity_model), description="Found opportunities"),
    "summary": fields.Nested(search_summary_model, description="Results summary"),
    "total_found": fields.Integer(description="Total opportunities found (before limiting)"),
    "search_query": fields.String(description="Natural language version of search"),
    "processing_time": fields.Float(description="Search processing time"),
    "timestamp": fields.String(description="Search timestamp")
})

@opportunities_ns.route("/find")
class FindOpportunities(Resource):
    """Find property opportunities based on criteria"""
    
    @opportunities_ns.doc("find_opportunities")
    @opportunities_ns.expect(opportunity_search_request)
    @opportunities_ns.marshal_with(opportunity_search_response)
    def post(self):
        """Search for property opportunities matching specific criteria"""
        data = request.get_json()
        
        if not data or "criteria" not in data:
            raise ValidationError("Search criteria is required")
        
        criteria = data["criteria"]
        limit = data.get("limit", 20)
        sort_by = data.get("sort_by", "value")
        
        # Validate limit
        if limit < 1 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")
        
        # Initialize search engine
        search_engine = SmartSearchEngine()
        
        # Find opportunities
        results = search_engine.find_opportunities(
            criteria=criteria,
            limit=limit,
            sort_by=sort_by
        )
        
        return results

@opportunities_ns.route("/quick-find")
class QuickFind(Resource):
    """Quick opportunity search with simplified criteria"""
    
    @opportunities_ns.doc("quick_find_opportunities")
    @opportunities_ns.param("max_price", "Maximum price")
    @opportunities_ns.param("neighborhoods", "Comma-separated list of neighborhoods")
    @opportunities_ns.param("property_type", "Property type (single-family, condo, multi-family)")
    @opportunities_ns.param("min_bedrooms", "Minimum bedrooms")
    @opportunities_ns.marshal_with(opportunity_search_response)
    def get(self):
        """Quick search for opportunities with basic criteria"""
        # Build criteria from query parameters
        criteria = {}
        
        if request.args.get("max_price"):
            try:
                criteria["max_price"] = float(request.args.get("max_price"))
            except ValueError:
                raise ValidationError("Invalid max_price value")
        
        if request.args.get("neighborhoods"):
            criteria["neighborhoods"] = [
                n.strip() for n in request.args.get("neighborhoods").split(",")
            ]
        
        if request.args.get("property_type"):
            criteria["property_type"] = request.args.get("property_type")
        
        if request.args.get("min_bedrooms"):
            try:
                criteria["min_bedrooms"] = int(request.args.get("min_bedrooms"))
            except ValueError:
                raise ValidationError("Invalid min_bedrooms value")
        
        # Initialize search engine
        search_engine = SmartSearchEngine()
        
        # Find opportunities
        results = search_engine.find_opportunities(
            criteria=criteria,
            limit=10,
            sort_by="value"
        )
        
        return results

@opportunities_ns.route("/investment")
class InvestmentOpportunities(Resource):
    """Find investment-specific opportunities"""
    
    @opportunities_ns.doc("find_investment_opportunities")
    @opportunities_ns.expect(opportunities_ns.model("InvestmentCriteria", {
        "budget_min": fields.Float(description="Minimum investment budget"),
        "budget_max": fields.Float(required=True, description="Maximum investment budget"),
        "min_cap_rate": fields.Float(description="Minimum cap rate (e.g., 8 for 8%)"),
        "property_types": fields.List(
            fields.String,
            description="Property types",
            default=["single-family", "multi-family"]
        ),
        "neighborhoods": fields.List(fields.String, description="Target neighborhoods"),
        "investment_strategy": fields.String(
            enum=["rental", "fix-flip", "both"],
            default="both",
            description="Investment strategy"
        )
    }))
    def post(self):
        """Find properties with high investment potential"""
        data = request.get_json()
        
        if not data or "budget_max" not in data:
            raise ValidationError("budget_max is required")
        
        # Build investment-focused criteria
        criteria = {
            "min_price": data.get("budget_min"),
            "max_price": data["budget_max"],
            "min_cap_rate": data.get("min_cap_rate"),
            "property_types": data.get("property_types", ["single-family", "multi-family"]),
            "neighborhoods": data.get("neighborhoods", [])
        }
        
        # Add strategy-specific criteria
        strategy = data.get("investment_strategy", "both")
        if strategy == "rental":
            criteria["rental_ready"] = True
        elif strategy == "fix-flip":
            criteria["fix_and_flip"] = True
            criteria["distressed"] = True
        
        # Initialize search engine
        search_engine = SmartSearchEngine()
        
        # Find opportunities with investment focus
        results = search_engine.find_opportunities(
            criteria=criteria,
            limit=25,
            sort_by="score"  # Sort by match score for investments
        )
        
        # Add investment-specific summary
        if results.get("opportunities"):
            self._add_investment_metrics(results)
        
        return results
    
    def _add_investment_metrics(self, results: dict) -> None:
        """Add investment-specific metrics to results"""
        opportunities = results.get("opportunities", [])
        
        if not opportunities:
            return
        
        # Calculate investment metrics
        total_investment = sum(
            opp.get("estimated_price", 0) 
            for opp in opportunities 
            if opp.get("estimated_price")
        )
        
        avg_price = total_investment / len(opportunities) if opportunities else 0
        
        # Find best cap rate opportunities
        cap_rate_opps = [
            opp for opp in opportunities
            if "cap rate" in opp.get("description", "").lower()
        ]
        
        results["investment_summary"] = {
            "total_opportunities": len(opportunities),
            "total_investment_needed": total_investment,
            "average_property_price": avg_price,
            "high_cap_rate_count": len(cap_rate_opps),
            "distressed_count": sum(
                1 for opp in opportunities
                if "distressed" in str(opp.get("match_reasons", [])).lower()
            )
        }

@opportunities_ns.route("/suggestions")
class OpportunitySuggestions(Resource):
    """Get suggested criteria adjustments"""
    
    @opportunities_ns.doc("get_search_suggestions")
    def post(self):
        """Get suggestions for improving search criteria based on previous results"""
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is required")
        
        criteria = data.get("criteria", {})
        previous_results = data.get("previous_results", {})
        
        # Initialize search engine
        search_engine = SmartSearchEngine()
        
        # Parse criteria
        search_criteria = search_engine._parse_criteria(criteria)
        
        # Get suggestions
        suggestions = search_engine.suggest_criteria_adjustments(
            search_criteria,
            previous_results
        )
        
        return {
            "suggestions": suggestions,
            "current_criteria": search_engine._criteria_to_dict(search_criteria)
        }