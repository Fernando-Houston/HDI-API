"""Houston building permits endpoints"""

from flask import request, g
from flask_restx import Namespace, Resource, fields
from datetime import datetime

from backend.services.permits_client import PermitsClient
from backend.utils.exceptions import ValidationError

permits_ns = Namespace("permits", description="Houston building permits data")

# Response models
permit_model = permits_ns.model("Permit", {
    "permit_number": fields.String(description="Permit number"),
    "permit_type": fields.String(description="Type of permit"),
    "description": fields.String(description="Permit description"),
    "address": fields.String(description="Property address"),
    "zip_code": fields.String(description="ZIP code"),
    "neighborhood": fields.String(description="Neighborhood"),
    "issue_date": fields.String(description="Issue date"),
    "estimated_cost": fields.Float(description="Estimated cost"),
    "status": fields.String(description="Permit status"),
    "contractor": fields.String(description="Contractor name"),
    "owner": fields.String(description="Owner name"),
    "work_description": fields.String(description="Description of work"),
    "is_major_renovation": fields.Boolean(description="Major renovation (>$50k)"),
    "is_new_construction": fields.Boolean(description="New construction"),
    "days_ago": fields.Integer(description="Days since issued")
})

permit_statistics_model = permits_ns.model("PermitStatistics", {
    "total_permits": fields.Integer(description="Total number of permits"),
    "total_value": fields.Float(description="Total estimated cost"),
    "average_value": fields.Float(description="Average permit value"),
    "permit_types": fields.Raw(description="Count by permit type"),
    "recent_activity": fields.String(description="Activity level description"),
    "recent_count_90_days": fields.Integer(description="Permits in last 90 days"),
    "major_renovations": fields.Integer(description="Major renovations count"),
    "new_construction": fields.Integer(description="New construction count")
})

neighborhood_trend_model = permits_ns.model("NeighborhoodTrend", {
    "neighborhood": fields.String(description="Neighborhood name"),
    "trend": fields.String(description="Trend description"),
    "monthly_average": fields.Float(description="Average permits per month"),
    "total_investment": fields.Float(description="Total investment amount"),
    "permit_count": fields.Integer(description="Total permits analyzed"),
    "months_analyzed": fields.Integer(description="Number of months analyzed"),
    "top_permit_types": fields.List(fields.Raw, description="Most common permit types")
})

@permits_ns.route("/by-address")
class PermitsByAddress(Resource):
    """Search permits by address"""
    
    @permits_ns.doc("search_permits_by_address")
    @permits_ns.param("address", "Property address", required=True)
    @permits_ns.param("days_back", "Number of days to look back (default: 365)")
    @permits_ns.param("permit_types", "Comma-separated permit types to filter")
    @permits_ns.marshal_list_with(permit_model)
    def get(self):
        """Get building permits for a specific address"""
        address = request.args.get("address")
        if not address:
            raise ValidationError("Address parameter is required")
        
        days_back = request.args.get("days_back", 365, type=int)
        permit_types_param = request.args.get("permit_types")
        
        # Parse permit types
        permit_types = None
        if permit_types_param:
            permit_types = [pt.strip() for pt in permit_types_param.split(",")]
        
        # Get permits
        with PermitsClient() as client:
            permits = client.search_permits_by_address(
                address=address,
                days_back=days_back,
                permit_types=permit_types
            )
        
        # Track usage
        g.query_cost = 0  # Permits API is free
        
        return permits

@permits_ns.route("/by-area")
class PermitsByArea(Resource):
    """Search permits by area"""
    
    @permits_ns.doc("search_permits_by_area")
    @permits_ns.param("zip_code", "ZIP code")
    @permits_ns.param("neighborhood", "Neighborhood name")
    @permits_ns.param("days_back", "Number of days to look back (default: 90)")
    @permits_ns.param("min_value", "Minimum permit value")
    @permits_ns.marshal_list_with(permit_model)
    def get(self):
        """Get building permits for an area (ZIP code or neighborhood)"""
        zip_code = request.args.get("zip_code")
        neighborhood = request.args.get("neighborhood")
        
        if not zip_code and not neighborhood:
            raise ValidationError("Either zip_code or neighborhood is required")
        
        days_back = request.args.get("days_back", 90, type=int)
        min_value = request.args.get("min_value", type=float)
        
        # Get permits
        with PermitsClient() as client:
            permits = client.search_permits_by_area(
                zip_code=zip_code,
                neighborhood=neighborhood,
                days_back=days_back,
                min_value=min_value
            )
        
        # Track usage
        g.query_cost = 0  # Permits API is free
        
        return permits

@permits_ns.route("/statistics")
class PermitStatistics(Resource):
    """Get permit statistics"""
    
    @permits_ns.doc("get_permit_statistics")
    @permits_ns.param("address", "Property address")
    @permits_ns.param("zip_code", "ZIP code")
    @permits_ns.param("neighborhood", "Neighborhood name")
    @permits_ns.param("days_back", "Number of days to analyze (default: 365)")
    @permits_ns.marshal_with(permit_statistics_model)
    def get(self):
        """Calculate statistics from permit data"""
        address = request.args.get("address")
        zip_code = request.args.get("zip_code")
        neighborhood = request.args.get("neighborhood")
        days_back = request.args.get("days_back", 365, type=int)
        
        if not any([address, zip_code, neighborhood]):
            raise ValidationError("At least one location parameter is required")
        
        with PermitsClient() as client:
            # Get permits based on parameters
            if address:
                permits = client.search_permits_by_address(address, days_back)
            else:
                permits = client.search_permits_by_area(
                    zip_code=zip_code,
                    neighborhood=neighborhood,
                    days_back=days_back
                )
            
            # Calculate statistics
            stats = client.get_permit_statistics(permits)
        
        return stats

@permits_ns.route("/trends/<string:neighborhood>")
class NeighborhoodTrends(Resource):
    """Get neighborhood permit trends"""
    
    @permits_ns.doc("get_neighborhood_trends")
    @permits_ns.param("months_back", "Number of months to analyze (default: 12)")
    @permits_ns.marshal_with(neighborhood_trend_model)
    def get(self, neighborhood):
        """Analyze permit trends for a neighborhood"""
        months_back = request.args.get("months_back", 12, type=int)
        
        if months_back < 1 or months_back > 60:
            raise ValidationError("months_back must be between 1 and 60")
        
        with PermitsClient() as client:
            trends = client.get_neighborhood_trends(
                neighborhood=neighborhood,
                months_back=months_back
            )
        
        return trends

@permits_ns.route("/property-intel")
class PropertyPermitIntelligence(Resource):
    """Enhanced property intelligence with permits"""
    
    @permits_ns.doc("get_property_permit_intelligence")
    @permits_ns.param("address", "Property address", required=True)
    def get(self):
        """Get comprehensive permit intelligence for a property"""
        address = request.args.get("address")
        if not address:
            raise ValidationError("Address parameter is required")
        
        with PermitsClient() as client:
            # Get permits for the property
            permits = client.search_permits_by_address(address, days_back=1825)  # 5 years
            
            # Get statistics
            stats = client.get_permit_statistics(permits)
            
            # Analyze permit history
            intelligence = {
                "address": address,
                "permit_summary": stats,
                "recent_permits": [p for p in permits if p.get("days_ago", 999) <= 180],
                "renovation_history": self._analyze_renovation_history(permits),
                "investment_signals": self._identify_investment_signals(permits, stats),
                "property_condition_indicators": self._assess_property_condition(permits)
            }
        
        return intelligence
    
    def _analyze_renovation_history(self, permits: list) -> dict:
        """Analyze renovation patterns"""
        renovations = [p for p in permits if p.get("is_major_renovation")]
        
        if not renovations:
            return {
                "major_renovations_count": 0,
                "total_investment": 0,
                "assessment": "No major renovations on record"
            }
        
        total_investment = sum(r.get("estimated_cost", 0) for r in renovations)
        recent_renovations = [r for r in renovations if r.get("days_ago", 999) <= 730]  # 2 years
        
        if recent_renovations:
            assessment = "Recently renovated - likely move-in ready"
        elif renovations:
            assessment = "Past renovations on record - may need updates"
        else:
            assessment = "Limited renovation history"
        
        return {
            "major_renovations_count": len(renovations),
            "total_investment": total_investment,
            "most_recent_renovation": renovations[0] if renovations else None,
            "recent_renovations_2yr": len(recent_renovations),
            "assessment": assessment
        }
    
    def _identify_investment_signals(self, permits: list, stats: dict) -> dict:
        """Identify investment-relevant signals from permits"""
        signals = []
        
        # Check for flipping activity
        if stats.get("major_renovations", 0) >= 2 and len(permits) > 0:
            first_date = min(p.get("issue_date", "9999") for p in permits)
            if self._calculate_years_between(first_date) <= 3:
                signals.append("Multiple major renovations - possible flip property")
        
        # Check for new construction
        if stats.get("new_construction", 0) > 0:
            signals.append("New construction on record")
        
        # Check for recent activity
        if stats.get("recent_count_90_days", 0) > 0:
            signals.append("Recent permit activity - property may be under renovation")
        
        # Check investment level
        if stats.get("total_value", 0) > 100000:
            signals.append(f"Significant investment: ${stats['total_value']:,.0f}")
        
        return {
            "signals": signals,
            "investment_grade": self._calculate_investment_grade(stats),
            "flip_potential": len(signals) > 2
        }
    
    def _assess_property_condition(self, permits: list) -> dict:
        """Assess property condition based on permits"""
        # Look for specific permit types that indicate condition
        roof_permits = [p for p in permits if "roof" in p.get("permit_type", "").lower()]
        plumbing_permits = [p for p in permits if "plumb" in p.get("permit_type", "").lower()]
        electrical_permits = [p for p in permits if "electric" in p.get("permit_type", "").lower()]
        hvac_permits = [p for p in permits if "hvac" in p.get("permit_type", "").lower() or "ac" in p.get("permit_type", "").lower()]
        
        systems_updated = {
            "roof": len(roof_permits) > 0,
            "plumbing": len(plumbing_permits) > 0,
            "electrical": len(electrical_permits) > 0,
            "hvac": len(hvac_permits) > 0
        }
        
        # Determine overall condition
        updated_systems = sum(1 for v in systems_updated.values() if v)
        
        if updated_systems >= 3:
            condition = "Excellent - major systems recently updated"
        elif updated_systems >= 2:
            condition = "Good - some major systems updated"
        elif updated_systems >= 1:
            condition = "Fair - limited updates on record"
        else:
            condition = "Unknown - no major system updates on record"
        
        return {
            "overall_condition": condition,
            "systems_updated": systems_updated,
            "updated_systems_count": updated_systems,
            "most_recent_updates": self._get_most_recent_by_type(permits)
        }
    
    def _calculate_years_between(self, date_str: str) -> float:
        """Calculate years between date and now"""
        try:
            date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            delta = datetime.now() - date
            return delta.days / 365.25
        except:
            return 999
    
    def _calculate_investment_grade(self, stats: dict) -> str:
        """Calculate investment grade based on permit history"""
        score = 0
        
        # Recent activity is positive
        if stats.get("recent_count_90_days", 0) > 0:
            score += 2
        
        # Major renovations are positive
        if stats.get("major_renovations", 0) > 0:
            score += 2
        
        # High total investment is positive
        if stats.get("total_value", 0) > 50000:
            score += 1
        if stats.get("total_value", 0) > 100000:
            score += 1
        
        # Map score to grade
        if score >= 5:
            return "A - Excellent investment potential"
        elif score >= 3:
            return "B - Good investment potential"
        elif score >= 1:
            return "C - Fair investment potential"
        else:
            return "D - Limited permit history"
    
    def _get_most_recent_by_type(self, permits: list) -> dict:
        """Get most recent permit by type"""
        by_type = {}
        
        for permit in permits:
            permit_type = permit.get("permit_type", "Unknown")
            if permit_type not in by_type or permit.get("days_ago", 999) < by_type[permit_type].get("days_ago", 999):
                by_type[permit_type] = permit
        
        return by_type