"""Smart search service for finding property opportunities"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
import re
import structlog

from backend.services.perplexity_client import PerplexityClient
from backend.services.hcad_client import HCADClient
from backend.services.data_fusion import DataFusionEngine
from backend.utils.exceptions import ValidationError

logger = structlog.get_logger(__name__)

@dataclass
class SearchCriteria:
    """Property search criteria"""
    # Price criteria
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # Investment criteria
    min_cap_rate: Optional[float] = None
    max_price_per_sqft: Optional[float] = None
    
    # Location criteria
    neighborhoods: List[str] = field(default_factory=list)
    zip_codes: List[str] = field(default_factory=list)
    school_districts: List[str] = field(default_factory=list)
    
    # Property criteria
    property_types: List[str] = field(default_factory=list)
    min_bedrooms: Optional[int] = None
    min_bathrooms: Optional[float] = None
    min_sqft: Optional[int] = None
    max_sqft: Optional[int] = None
    min_lot_size: Optional[int] = None
    year_built_after: Optional[int] = None
    
    # Special criteria
    distressed: Optional[bool] = None
    pre_foreclosure: Optional[bool] = None
    new_construction: Optional[bool] = None
    pool: Optional[bool] = None
    garage: Optional[bool] = None
    
    # Investment specific
    rental_ready: Optional[bool] = None
    fix_and_flip: Optional[bool] = None
    multi_family: Optional[bool] = None
    
    def to_query_string(self) -> str:
        """Convert criteria to natural language query"""
        parts = []
        
        # Price range
        if self.min_price and self.max_price:
            parts.append(f"priced between ${self.min_price:,.0f} and ${self.max_price:,.0f}")
        elif self.max_price:
            parts.append(f"under ${self.max_price:,.0f}")
        elif self.min_price:
            parts.append(f"over ${self.min_price:,.0f}")
        
        # Property type
        if self.property_types:
            parts.append(f"{', '.join(self.property_types)} properties")
        
        # Location
        if self.neighborhoods:
            parts.append(f"in {', '.join(self.neighborhoods)}")
        elif self.zip_codes:
            parts.append(f"in zip codes {', '.join(self.zip_codes)}")
        
        # Bedrooms/bathrooms
        if self.min_bedrooms:
            parts.append(f"with {self.min_bedrooms}+ bedrooms")
        if self.min_bathrooms:
            parts.append(f"with {self.min_bathrooms}+ bathrooms")
        
        # Size
        if self.min_sqft:
            parts.append(f"at least {self.min_sqft:,} sqft")
        
        # Special features
        if self.distressed:
            parts.append("distressed or motivated seller")
        if self.new_construction:
            parts.append("new construction")
        if self.multi_family:
            parts.append("multi-family")
        
        # Investment criteria
        if self.min_cap_rate:
            parts.append(f"with {self.min_cap_rate}%+ cap rate")
        
        return "Houston real estate: " + ", ".join(parts) if parts else "Houston properties"

class SmartSearchEngine:
    """Engine for intelligent property searching"""
    
    def __init__(self):
        self.perplexity = PerplexityClient()
        self.hcad = HCADClient()
        self.fusion = DataFusionEngine()
        logger.info("SmartSearchEngine initialized")
    
    def find_opportunities(
        self,
        criteria: Union[Dict[str, Any], SearchCriteria],
        limit: int = 20,
        sort_by: str = "value"
    ) -> Dict[str, Any]:
        """
        Find property opportunities based on criteria
        
        Args:
            criteria: Search criteria (dict or SearchCriteria object)
            limit: Maximum number of results
            sort_by: Sort results by (value, cap_rate, potential, date)
            
        Returns:
            Search results with opportunities
        """
        start_time = datetime.utcnow()
        
        # Convert dict to SearchCriteria if needed
        if isinstance(criteria, dict):
            criteria = self._parse_criteria(criteria)
        
        logger.info("Starting smart search", criteria=criteria)
        
        # Build and execute search
        results = {
            "criteria": self._criteria_to_dict(criteria),
            "timestamp": datetime.utcnow().isoformat(),
            "opportunities": [],
            "summary": {},
            "search_query": criteria.to_query_string()
        }
        
        try:
            # Step 1: Use Perplexity to find matching properties
            perplexity_results = self._search_with_perplexity(criteria, limit)
            
            # Step 2: Score and rank opportunities
            opportunities = self._score_opportunities(perplexity_results, criteria)
            
            # Step 3: Sort results
            sorted_opportunities = self._sort_opportunities(opportunities, sort_by)
            
            # Step 4: Limit results
            results["opportunities"] = sorted_opportunities[:limit]
            
            # Step 5: Generate summary
            results["summary"] = self._generate_summary(results["opportunities"], criteria)
            
            # Add metadata
            results["total_found"] = len(opportunities)
            results["processing_time"] = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                "Smart search completed",
                found=len(opportunities),
                returned=len(results["opportunities"]),
                time=results["processing_time"]
            )
            
        except Exception as e:
            logger.error("Smart search failed", error=str(e))
            results["error"] = str(e)
            results["opportunities"] = []
        
        return results
    
    def _parse_criteria(self, criteria_dict: Dict[str, Any]) -> SearchCriteria:
        """Parse criteria dictionary into SearchCriteria object"""
        criteria = SearchCriteria()
        
        # Price criteria
        criteria.min_price = criteria_dict.get("min_price")
        criteria.max_price = criteria_dict.get("max_price")
        
        # Investment criteria
        criteria.min_cap_rate = criteria_dict.get("min_cap_rate")
        criteria.max_price_per_sqft = criteria_dict.get("max_price_per_sqft")
        
        # Location criteria
        criteria.neighborhoods = criteria_dict.get("neighborhoods", [])
        criteria.zip_codes = criteria_dict.get("zip_codes", [])
        criteria.school_districts = criteria_dict.get("school_districts", [])
        
        # Property criteria
        criteria.property_types = criteria_dict.get("property_types", [])
        if not criteria.property_types and criteria_dict.get("property_type"):
            criteria.property_types = [criteria_dict["property_type"]]
        
        criteria.min_bedrooms = criteria_dict.get("min_bedrooms")
        criteria.min_bathrooms = criteria_dict.get("min_bathrooms")
        criteria.min_sqft = criteria_dict.get("min_sqft")
        criteria.max_sqft = criteria_dict.get("max_sqft")
        criteria.min_lot_size = criteria_dict.get("min_lot_size")
        criteria.year_built_after = criteria_dict.get("year_built_after")
        
        # Special criteria
        criteria.distressed = criteria_dict.get("distressed")
        criteria.pre_foreclosure = criteria_dict.get("pre_foreclosure")
        criteria.new_construction = criteria_dict.get("new_construction")
        criteria.pool = criteria_dict.get("pool")
        criteria.garage = criteria_dict.get("garage")
        
        # Investment specific
        criteria.rental_ready = criteria_dict.get("rental_ready")
        criteria.fix_and_flip = criteria_dict.get("fix_and_flip")
        criteria.multi_family = criteria_dict.get("multi_family")
        
        return criteria
    
    def _criteria_to_dict(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Convert SearchCriteria to dictionary"""
        return {
            k: v for k, v in criteria.__dict__.items() 
            if v is not None and (not isinstance(v, list) or v)
        }
    
    def _search_with_perplexity(self, criteria: SearchCriteria, limit: int) -> List[Dict[str, Any]]:
        """Search for properties using Perplexity"""
        # Build detailed search query
        query = f"""
        Find current {limit} property opportunities in Houston that match these criteria:
        {criteria.to_query_string()}
        
        For each property, provide:
        - Address or area
        - Estimated price or price range
        - Key features (bedrooms, bathrooms, sqft)
        - Why it's a good opportunity
        - Any special circumstances (distressed, new construction, etc.)
        
        Focus on properties currently available or recently listed.
        Format as a list with specific details.
        """
        
        response = self.perplexity.query(query)
        
        if not response.get("success"):
            return []
        
        # Parse Perplexity response into structured opportunities
        return self._parse_perplexity_response(response.get("data", ""), criteria)
    
    def _parse_perplexity_response(self, response_text: str, criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """Parse Perplexity response into structured property data"""
        opportunities = []
        
        # Split response into sections (this is a simplified parser)
        # In production, you'd want more sophisticated parsing
        lines = response_text.split('\n')
        current_property = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_property:
                    opportunities.append(current_property)
                    current_property = {}
                continue
            
            # Look for address patterns
            address_match = re.search(r'\d+\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)', line, re.IGNORECASE)
            if address_match:
                if current_property:
                    opportunities.append(current_property)
                current_property = {
                    "address": address_match.group(0),
                    "source": "perplexity",
                    "raw_text": line
                }
            
            # Look for price patterns
            price_match = re.search(r'\$([0-9,]+)', line)
            if price_match and current_property:
                price_str = price_match.group(1).replace(',', '')
                current_property["estimated_price"] = float(price_str)
            
            # Look for bedroom/bathroom patterns
            bed_match = re.search(r'(\d+)\s*(?:bed|bedroom|br)', line, re.IGNORECASE)
            if bed_match and current_property:
                current_property["bedrooms"] = int(bed_match.group(1))
            
            bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom|ba)', line, re.IGNORECASE)
            if bath_match and current_property:
                current_property["bathrooms"] = float(bath_match.group(1))
            
            # Look for sqft
            sqft_match = re.search(r'([0-9,]+)\s*(?:sq\.?\s*ft\.?|sqft)', line, re.IGNORECASE)
            if sqft_match and current_property:
                current_property["sqft"] = int(sqft_match.group(1).replace(',', ''))
            
            # Store all text for this property
            if current_property:
                current_property["description"] = current_property.get("description", "") + " " + line
        
        # Don't forget the last property
        if current_property:
            opportunities.append(current_property)
        
        return opportunities
    
    def _score_opportunities(self, opportunities: List[Dict[str, Any]], criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """Score each opportunity based on how well it matches criteria"""
        scored_opportunities = []
        
        for opp in opportunities:
            score = 0.0
            match_reasons = []
            
            # Price scoring
            if criteria.max_price and opp.get("estimated_price"):
                if opp["estimated_price"] <= criteria.max_price:
                    score += 2.0
                    price_discount = (criteria.max_price - opp["estimated_price"]) / criteria.max_price
                    score += price_discount * 3.0  # Bonus for being under budget
                    match_reasons.append(f"Under budget by ${criteria.max_price - opp['estimated_price']:,.0f}")
            
            # Bedroom scoring
            if criteria.min_bedrooms and opp.get("bedrooms"):
                if opp["bedrooms"] >= criteria.min_bedrooms:
                    score += 1.0
                    if opp["bedrooms"] > criteria.min_bedrooms:
                        score += 0.5  # Bonus for extra bedrooms
                        match_reasons.append(f"{opp['bedrooms']} bedrooms (exceeds requirement)")
            
            # Size scoring
            if criteria.min_sqft and opp.get("sqft"):
                if opp["sqft"] >= criteria.min_sqft:
                    score += 1.0
                    match_reasons.append(f"{opp['sqft']:,} sqft")
            
            # Special features scoring
            description = opp.get("description", "").lower()
            if criteria.distressed and ("distressed" in description or "motivated" in description):
                score += 3.0
                match_reasons.append("Distressed/motivated seller")
            
            if criteria.new_construction and "new construction" in description:
                score += 2.0
                match_reasons.append("New construction")
            
            if criteria.multi_family and ("multi" in description or "duplex" in description or "units" in description):
                score += 2.0
                match_reasons.append("Multi-family property")
            
            # Investment potential scoring
            if "high roi" in description or "investment" in description or "rental" in description:
                score += 1.5
                match_reasons.append("High investment potential")
            
            if "below market" in description or "undervalued" in description:
                score += 2.5
                match_reasons.append("Below market value")
            
            # Add score and reasons to opportunity
            opp["match_score"] = score
            opp["match_reasons"] = match_reasons
            opp["matches_criteria"] = score > 0
            
            if score > 0:
                scored_opportunities.append(opp)
        
        return scored_opportunities
    
    def _sort_opportunities(self, opportunities: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort opportunities by specified criteria"""
        if sort_by == "score":
            return sorted(opportunities, key=lambda x: x.get("match_score", 0), reverse=True)
        elif sort_by == "price":
            return sorted(opportunities, key=lambda x: x.get("estimated_price", float('inf')))
        elif sort_by == "value":
            # Sort by price per sqft if available, otherwise by score
            def value_key(opp):
                if opp.get("estimated_price") and opp.get("sqft"):
                    return opp["estimated_price"] / opp["sqft"]
                return -opp.get("match_score", 0)  # Negative to sort high scores first
            return sorted(opportunities, key=value_key)
        else:
            # Default to score
            return sorted(opportunities, key=lambda x: x.get("match_score", 0), reverse=True)
    
    def _generate_summary(self, opportunities: List[Dict[str, Any]], criteria: SearchCriteria) -> Dict[str, Any]:
        """Generate summary of search results"""
        if not opportunities:
            return {"message": "No opportunities found matching criteria"}
        
        # Calculate statistics
        prices = [opp.get("estimated_price", 0) for opp in opportunities if opp.get("estimated_price")]
        
        summary = {
            "total_opportunities": len(opportunities),
            "average_match_score": sum(opp.get("match_score", 0) for opp in opportunities) / len(opportunities),
            "top_reasons": self._get_top_match_reasons(opportunities),
        }
        
        if prices:
            summary["price_range"] = {
                "min": min(prices),
                "max": max(prices),
                "average": sum(prices) / len(prices)
            }
        
        # Get neighborhood distribution
        neighborhoods = {}
        for opp in opportunities:
            # Try to extract neighborhood from address or description
            desc = opp.get("description", "")
            for neighborhood in ["Heights", "Montrose", "River Oaks", "Medical Center", "Galleria", "Midtown", "Downtown"]:
                if neighborhood.lower() in desc.lower():
                    neighborhoods[neighborhood] = neighborhoods.get(neighborhood, 0) + 1
        
        if neighborhoods:
            summary["neighborhoods"] = neighborhoods
        
        return summary
    
    def _get_top_match_reasons(self, opportunities: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, int]]:
        """Get most common match reasons"""
        reason_counts = {}
        
        for opp in opportunities:
            for reason in opp.get("match_reasons", []):
                # Normalize reason
                normalized = reason.split("(")[0].strip()
                reason_counts[normalized] = reason_counts.get(normalized, 0) + 1
        
        # Sort by count
        sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [{"reason": reason, "count": count} for reason, count in sorted_reasons[:top_n]]
    
    def suggest_criteria_adjustments(self, criteria: SearchCriteria, results: Dict[str, Any]) -> List[str]:
        """Suggest adjustments to criteria based on results"""
        suggestions = []
        
        opportunities = results.get("opportunities", [])
        
        if not opportunities:
            # No results - suggest loosening criteria
            if criteria.max_price:
                suggestions.append(f"Try increasing max price to ${criteria.max_price * 1.2:,.0f}")
            if criteria.neighborhoods:
                suggestions.append("Try expanding to nearby neighborhoods")
            if criteria.min_bedrooms and criteria.min_bedrooms > 2:
                suggestions.append(f"Consider reducing to {criteria.min_bedrooms - 1} bedrooms")
        
        elif len(opportunities) < 5:
            # Few results - suggest minor adjustments
            suggestions.append("Limited opportunities found - consider slight adjustments to criteria")
        
        else:
            # Many results - could tighten criteria
            prices = [opp.get("estimated_price", 0) for opp in opportunities if opp.get("estimated_price")]
            if prices and criteria.max_price:
                avg_price = sum(prices) / len(prices)
                if avg_price < criteria.max_price * 0.7:
                    suggestions.append(f"Many options available - could lower max price to ${avg_price * 1.1:,.0f}")
        
        return suggestions