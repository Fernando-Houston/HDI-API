"""Data fusion engine for combining multiple data sources"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from backend.services.perplexity_client import PerplexityClient
from backend.services.postgres_hcad_client import PostgresHCADClient
from backend.services.permits_client import PermitsClient
from backend.utils.exceptions import DataFusionError

logger = structlog.get_logger(__name__)

class DataFusionEngine:
    """Combines data from multiple sources intelligently"""
    
    def __init__(self):
        """Initialize data fusion engine"""
        self.perplexity = PerplexityClient()
        # Use the PostgreSQL-based HCAD client
        self.hcad = PostgresHCADClient()
        self.permits = PermitsClient()
        logger.info("DataFusionEngine initialized with PostgreSQL HCAD client")
    
    def get_property_intelligence(self, address: str) -> Dict[str, Any]:
        """
        Get comprehensive property intelligence by combining sources
        
        Args:
            address: Property address
            
        Returns:
            Combined property intelligence
        """
        try:
            logger.info("Getting property intelligence", address=address)
            
            # Initialize response structure
            intelligence = {
                "address": address,
                "timestamp": datetime.utcnow().isoformat(),
                "sources": {},
                "insights": {},
                "confidence_score": 0.0
            }
            
            # Get HCAD official data
            try:
                hcad_data = self.hcad.get_property_by_address(address)
                if hcad_data:
                    intelligence["sources"]["hcad"] = hcad_data
                    intelligence["official_data"] = self._extract_hcad_highlights(hcad_data)
            except Exception as e:
                logger.warning("HCAD lookup failed", error=str(e), address=address)
                intelligence["sources"]["hcad"] = {"error": str(e)}
            
            # Get Perplexity market insights
            try:
                perplexity_prompt = self._build_property_prompt(address, intelligence.get("official_data"))
                perplexity_data = self.perplexity.query(perplexity_prompt)
                
                if perplexity_data.get("success"):
                    intelligence["sources"]["perplexity"] = perplexity_data
                    intelligence["market_insights"] = perplexity_data.get("data")
            except Exception as e:
                logger.warning("Perplexity lookup failed", error=str(e), address=address)
                intelligence["sources"]["perplexity"] = {"error": str(e)}
            
            # Get Houston permits data
            try:
                permits_data = self.permits.search_permits_by_address(address, days_back=1825)  # 5 years
                if permits_data:
                    permits_stats = self.permits.get_permit_statistics(permits_data)
                    intelligence["sources"]["permits"] = {
                        "permits": permits_data[:10],  # Most recent 10
                        "statistics": permits_stats
                    }
                    intelligence["permit_insights"] = self._extract_permit_insights(permits_data, permits_stats)
            except Exception as e:
                logger.warning("Permits lookup failed", error=str(e), address=address)
                intelligence["sources"]["permits"] = {"error": str(e)}
            
            # Combine insights
            intelligence["combined_analysis"] = self._combine_insights(intelligence)
            
            # Calculate confidence score
            intelligence["confidence_score"] = self._calculate_confidence(intelligence)
            
            # Add recommendations
            intelligence["recommendations"] = self._generate_recommendations(intelligence)
            
            logger.info("Property intelligence compiled", address=address, sources=list(intelligence["sources"].keys()))
            return intelligence
            
        except Exception as e:
            logger.error("Data fusion failed", error=str(e), address=address)
            raise DataFusionError(f"Failed to get property intelligence: {str(e)}")
    
    def get_market_intelligence(self, area: str, include_developments: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive market intelligence for an area
        
        Args:
            area: Houston area/neighborhood name
            include_developments: Whether to include development data
            
        Returns:
            Combined market intelligence
        """
        try:
            logger.info("Getting market intelligence", area=area)
            
            intelligence = {
                "area": area,
                "timestamp": datetime.utcnow().isoformat(),
                "sources": {},
                "analysis": {}
            }
            
            # Get Perplexity market data
            try:
                market_response = self.perplexity.query_with_template(
                    "market_overview",
                    area=area,
                    date=datetime.now().strftime("%B %Y")
                )
                
                if market_response.get("success"):
                    intelligence["sources"]["market_data"] = market_response
                    intelligence["analysis"]["market_overview"] = market_response.get("data")
            except Exception as e:
                logger.warning("Market data lookup failed", error=str(e))
                intelligence["sources"]["market_data"] = {"error": str(e)}
            
            # Get investment opportunities
            try:
                investment_response = self.perplexity.query_with_template(
                    "investment_opportunities",
                    area=area,
                    budget="$300,000-$800,000"  # Default range
                )
                
                if investment_response.get("success"):
                    intelligence["sources"]["investment_data"] = investment_response
                    intelligence["analysis"]["investment_opportunities"] = investment_response.get("data")
            except Exception as e:
                logger.warning("Investment data lookup failed", error=str(e))
            
            # Get development data if requested
            if include_developments:
                try:
                    dev_response = self.perplexity.query_with_template(
                        "development_tracker",
                        area=area
                    )
                    
                    if dev_response.get("success"):
                        intelligence["sources"]["development_data"] = dev_response
                        intelligence["analysis"]["active_developments"] = dev_response.get("data")
                except Exception as e:
                    logger.warning("Development data lookup failed", error=str(e))
            
            # Generate executive summary
            intelligence["executive_summary"] = self._generate_market_summary(intelligence)
            
            return intelligence
            
        except Exception as e:
            logger.error("Market intelligence failed", error=str(e), area=area)
            raise DataFusionError(f"Failed to get market intelligence: {str(e)}")
    
    def compare_neighborhoods(self, area1: str, area2: str) -> Dict[str, Any]:
        """
        Compare two Houston neighborhoods
        
        Args:
            area1: First neighborhood
            area2: Second neighborhood
            
        Returns:
            Comparative analysis
        """
        try:
            comparison_response = self.perplexity.query_with_template(
                "comparative_analysis",
                area1=area1,
                area2=area2
            )
            
            return {
                "comparison": comparison_response.get("data") if comparison_response.get("success") else None,
                "metadata": comparison_response.get("metadata", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Neighborhood comparison failed", error=str(e))
            raise DataFusionError(f"Failed to compare neighborhoods: {str(e)}")
    
    def _extract_hcad_highlights(self, hcad_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key information from HCAD data"""
        highlights = {}
        
        # Extract values
        if "values" in hcad_data:
            highlights["appraised_value"] = hcad_data["values"].get("Total", "Unknown")
            highlights["land_value"] = hcad_data["values"].get("Land", "Unknown")
            highlights["improvement_value"] = hcad_data["values"].get("Improvement", "Unknown")
        
        # Extract property info
        if "property_info" in hcad_data:
            info = hcad_data["property_info"]
            highlights["property_type"] = info.get("property_type", "Unknown")
            highlights["year_built"] = info.get("year_built", "Unknown")
            highlights["living_area"] = info.get("living_area", "Unknown")
            highlights["land_area"] = info.get("land_area", "Unknown")
        
        # Extract ownership
        if "ownership" in hcad_data:
            highlights["owner"] = hcad_data["ownership"].get("owner_name", "Unknown")
        
        # Extract tax info
        if "tax_info" in hcad_data:
            highlights["taxes"] = hcad_data["tax_info"]
        
        return highlights
    
    def _build_property_prompt(self, address: str, official_data: Optional[Dict] = None) -> str:
        """Build an enhanced prompt using official data"""
        prompt = f"Provide current market analysis for property at {address}, Houston, TX."
        
        if official_data:
            prompt += f"\n\nOfficial property data:"
            if "appraised_value" in official_data:
                prompt += f"\n- Appraised value: {official_data['appraised_value']}"
            if "year_built" in official_data:
                prompt += f"\n- Year built: {official_data['year_built']}"
            if "living_area" in official_data:
                prompt += f"\n- Living area: {official_data['living_area']}"
        
        prompt += "\n\nAnalyze: market value vs appraisal, comparable sales, investment potential, and market trends for this area."
        
        return prompt
    
    def _combine_insights(self, intelligence: Dict[str, Any]) -> Dict[str, Any]:
        """Combine insights from multiple sources"""
        combined = {
            "has_official_data": "hcad" in intelligence["sources"] and not intelligence["sources"]["hcad"].get("error"),
            "has_market_data": "perplexity" in intelligence["sources"] and not intelligence["sources"]["perplexity"].get("error"),
            "has_permit_data": "permits" in intelligence["sources"] and not intelligence["sources"]["permits"].get("error"),
            "data_quality": "high" if all(not s.get("error") for s in intelligence["sources"].values()) else "partial"
        }
        
        # Add key insights
        if intelligence.get("official_data"):
            combined["official_value"] = intelligence["official_data"].get("appraised_value", "Unknown")
        
        if intelligence.get("permit_insights"):
            combined["renovation_status"] = intelligence["permit_insights"].get("renovation_status", "Unknown")
            combined["total_investment"] = intelligence["permit_insights"].get("investment_level", 0)
        
        return combined
    
    def _calculate_confidence(self, intelligence: Dict[str, Any]) -> float:
        """Calculate confidence score based on available data"""
        score = 0.0
        
        # HCAD data adds 40% confidence
        if intelligence["sources"].get("hcad") and not intelligence["sources"]["hcad"].get("error"):
            score += 0.4
        
        # Perplexity data adds 30% confidence
        if intelligence["sources"].get("perplexity") and not intelligence["sources"]["perplexity"].get("error"):
            score += 0.3
        
        # Permits data adds 20% confidence
        if intelligence["sources"].get("permits") and not intelligence["sources"]["permits"].get("error"):
            score += 0.2
        
        # Data freshness adds 10%
        score += 0.1  # Always fresh for now
        
        return min(score, 1.0)
    
    def _generate_recommendations(self, intelligence: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if intelligence["confidence_score"] < 0.5:
            recommendations.append("Limited data available - consider additional research")
        
        if intelligence.get("official_data", {}).get("appraised_value"):
            recommendations.append("Compare appraised value with recent comparable sales")
        
        # Permit-based recommendations
        permit_insights = intelligence.get("permit_insights", {})
        if permit_insights.get("recent_activity"):
            recommendations.append("Property under active renovation - verify completion status")
        elif permit_insights.get("investment_level", 0) > 50000:
            recommendations.append(f"Significant investment of ${permit_insights['investment_level']:,.0f} in improvements")
        
        if not permit_insights.get("property_improvements"):
            recommendations.append("No recent permits - consider inspection for deferred maintenance")
        
        recommendations.append("Review neighborhood trends and future development plans")
        
        return recommendations
    
    def _generate_market_summary(self, intelligence: Dict[str, Any]) -> str:
        """Generate executive summary of market intelligence"""
        summary_parts = []
        
        if intelligence["analysis"].get("market_overview"):
            summary_parts.append("Market Overview: " + intelligence["analysis"]["market_overview"][:200] + "...")
        
        if intelligence["analysis"].get("investment_opportunities"):
            summary_parts.append("Investment Potential: Strong opportunities identified")
        
        if intelligence["analysis"].get("active_developments"):
            summary_parts.append("Development Activity: New projects underway")
        
        return " | ".join(summary_parts) if summary_parts else "Limited market data available"
    
    def _extract_permit_insights(self, permits: List[Dict[str, Any]], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from permit data"""
        insights = {
            "renovation_status": "Unknown",
            "investment_level": 0,
            "recent_activity": False,
            "property_improvements": []
        }
        
        if not permits:
            insights["renovation_status"] = "No recent permits"
            return insights
        
        # Analyze recent activity
        recent_permits = [p for p in permits if p.get("days_ago", 999) <= 180]
        if recent_permits:
            insights["recent_activity"] = True
            insights["renovation_status"] = "Active renovation/construction"
        elif stats.get("recent_count_90_days", 0) > 0:
            insights["renovation_status"] = "Recent work completed"
        else:
            insights["renovation_status"] = "No recent construction activity"
        
        # Calculate investment level
        insights["investment_level"] = stats.get("total_value", 0)
        
        # Identify improvements
        improvements = []
        if stats.get("major_renovations", 0) > 0:
            improvements.append(f"{stats['major_renovations']} major renovations")
        if stats.get("new_construction", 0) > 0:
            improvements.append("New construction")
        
        # Check for specific system updates
        for permit in permits[:20]:  # Check recent 20
            permit_type = permit.get("permit_type", "").lower()
            if "roof" in permit_type and "Roof updated" not in improvements:
                improvements.append("Roof updated")
            elif "plumb" in permit_type and "Plumbing updated" not in improvements:
                improvements.append("Plumbing updated")
            elif "electric" in permit_type and "Electrical updated" not in improvements:
                improvements.append("Electrical updated")
            elif "hvac" in permit_type or "ac" in permit_type and "HVAC updated" not in improvements:
                improvements.append("HVAC updated")
        
        insights["property_improvements"] = improvements
        
        return insights