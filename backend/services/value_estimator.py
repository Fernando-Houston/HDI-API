"""Property value estimation service for $0 properties"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
import statistics
import structlog
from math import radians, cos, sin, asin, sqrt

from backend.services.perplexity_client import PerplexityClient

logger = structlog.get_logger(__name__)

class PropertyValueEstimator:
    """Estimates property values using nearest neighbors and AI"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.perplexity = PerplexityClient()
        
    def estimate_property_value(self, property_data: Dict) -> Dict:
        """
        Estimate value for properties showing $0
        Uses Method 3: Both nearest properties + AI verification
        """
        if property_data.get('market_value', 0) > 0:
            # Property already has value
            return {
                'estimated': False,
                'value': property_data['market_value'],
                'confidence': 1.0,
                'method': 'actual'
            }
        
        # Get property details
        lat = property_data.get('latitude') or property_data.get('geometry', {}).get('centroid', {}).get('lat')
        lon = property_data.get('longitude') or property_data.get('geometry', {}).get('centroid', {}).get('lon')
        property_type = property_data.get('property_type', '')
        address = property_data.get('property_address', '')
        sqft = property_data.get('building_sqft', 0)
        
        # Method 1: Find nearest similar properties
        comparables = self._find_comparable_properties(
            lat, lon, property_type, 
            property_data.get('property_class', ''),
            limit=10
        )
        
        neighbor_estimate = None
        neighbor_confidence = 0
        
        if comparables:
            # Calculate estimate from neighbors
            values = [c['total_value'] for c in comparables if c['total_value'] > 0]
            if values:
                # Use median for robustness
                neighbor_estimate = statistics.median(values)
                
                # Adjust for square footage if available
                if sqft > 0 and comparables[0].get('area_sqft', 0) > 0:
                    avg_price_per_sqft = statistics.mean([
                        c['total_value'] / c['area_sqft'] 
                        for c in comparables 
                        if c['total_value'] > 0 and c['area_sqft'] > 0
                    ])
                    sqft_based_estimate = avg_price_per_sqft * sqft
                    # Blend estimates
                    neighbor_estimate = (neighbor_estimate + sqft_based_estimate) / 2
                
                # Calculate confidence based on data quality
                neighbor_confidence = min(0.8, len(values) / 10)  # Max 0.8 confidence
        
        # Method 2: AI verification and enhancement
        ai_estimate = None
        ai_confidence = 0
        
        if address:
            ai_result = self._get_ai_estimate(address, property_data, comparables)
            if ai_result:
                ai_estimate = ai_result['estimate']
                ai_confidence = ai_result['confidence']
        
        # Combine estimates
        final_estimate, final_confidence, method = self._combine_estimates(
            neighbor_estimate, neighbor_confidence,
            ai_estimate, ai_confidence
        )
        
        # Prepare result
        result = {
            'estimated': True,
            'value': final_estimate,
            'confidence': final_confidence,
            'method': method,
            'comparables_used': len(comparables),
            'estimation_details': {
                'neighbor_based': neighbor_estimate,
                'ai_based': ai_estimate,
                'comparable_properties': [
                    {
                        'address': c['property_address'],
                        'value': c['total_value'],
                        'distance_miles': c['distance_miles']
                    } for c in comparables[:5]
                ] if comparables else []
            }
        }
        
        logger.info("Property value estimated", 
                   address=address, 
                   estimate=final_estimate,
                   confidence=final_confidence)
        
        return result
    
    def _find_comparable_properties(self, lat: float, lon: float, 
                                   property_type: str, property_class: str,
                                   limit: int = 10) -> List[Dict]:
        """Find nearest similar properties with values"""
        if not lat or not lon:
            return []
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Query for nearby properties of same type
                    query = """
                    SELECT 
                        property_address,
                        total_value,
                        area_sqft,
                        year_built,
                        centroid_lat,
                        centroid_lon,
                        (3959 * acos(cos(radians(%s)) * cos(radians(centroid_lat)) * 
                         cos(radians(centroid_lon) - radians(%s)) + 
                         sin(radians(%s)) * sin(radians(centroid_lat)))) AS distance_miles
                    FROM properties
                    WHERE property_type = %s
                    AND total_value > 0
                    AND centroid_lat IS NOT NULL
                    AND centroid_lon IS NOT NULL
                    AND centroid_lat BETWEEN %s - 0.02 AND %s + 0.02
                    AND centroid_lon BETWEEN %s - 0.02 AND %s + 0.02
                    ORDER BY distance_miles
                    LIMIT %s
                    """
                    
                    cur.execute(query, (
                        lat, lon, lat, property_type,
                        lat, lat, lon, lon, limit
                    ))
                    
                    results = cur.fetchall()
                    return [dict(row) for row in results]
                    
        except Exception as e:
            logger.error(f"Error finding comparables: {str(e)}")
            return []
    
    def _get_ai_estimate(self, address: str, property_data: Dict, 
                        comparables: List[Dict]) -> Optional[Dict]:
        """Get AI-based estimate using Perplexity"""
        try:
            # Build context for AI
            context_parts = [
                f"Property at {address}",
                f"Type: {property_data.get('property_type', 'Unknown')}",
            ]
            
            if property_data.get('building_sqft', 0) > 0:
                context_parts.append(f"Size: {property_data['building_sqft']:,} sqft")
            
            if property_data.get('year_built'):
                context_parts.append(f"Built: {property_data['year_built']}")
            
            if comparables:
                avg_comp_value = statistics.mean([c['total_value'] for c in comparables[:5]])
                context_parts.append(f"Nearby similar properties average: ${avg_comp_value:,.0f}")
            
            context = ". ".join(context_parts)
            
            # Query Perplexity
            prompt = f"""
            Estimate the market value for this Houston property: {context}
            
            Provide a specific dollar amount estimate based on current Houston real estate market conditions.
            Format: Return only the number without $ or commas.
            """
            
            result = self.perplexity.query(prompt, temperature=0.1)
            
            if result.get('success'):
                # Extract number from response
                response_text = result.get('data', '')
                
                # Try to extract a number
                import re
                numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', response_text.replace(',', ''))
                
                if numbers:
                    # Take the first reasonable number (likely the estimate)
                    for num_str in numbers:
                        num = float(num_str)
                        if 10000 < num < 100000000:  # Reasonable property value range
                            return {
                                'estimate': num,
                                'confidence': 0.7,  # AI estimates get 0.7 confidence
                                'source': 'perplexity'
                            }
            
        except Exception as e:
            logger.error(f"AI estimation error: {str(e)}")
        
        return None
    
    def _combine_estimates(self, neighbor_est: Optional[float], neighbor_conf: float,
                          ai_est: Optional[float], ai_conf: float) -> Tuple[float, float, str]:
        """Combine neighbor and AI estimates using confidence weighting"""
        
        # Handle cases where we only have one estimate
        if neighbor_est and not ai_est:
            return neighbor_est, neighbor_conf, "neighbor_only"
        
        if ai_est and not neighbor_est:
            return ai_est, ai_conf, "ai_only"
        
        if not neighbor_est and not ai_est:
            return 0, 0, "no_estimate"
        
        # Both estimates available - weighted average
        total_conf = neighbor_conf + ai_conf
        
        if total_conf == 0:
            # Equal weight if no confidence
            final_est = (neighbor_est + ai_est) / 2
            final_conf = 0.5
        else:
            # Confidence-weighted average
            final_est = (
                (neighbor_est * neighbor_conf + ai_est * ai_conf) / 
                total_conf
            )
            final_conf = min(0.9, total_conf / 2)  # Cap at 0.9
        
        # Check if estimates agree (within 20%)
        if abs(neighbor_est - ai_est) / max(neighbor_est, ai_est) < 0.2:
            final_conf = min(0.95, final_conf + 0.1)  # Boost confidence if they agree
            method = "combined_agreement"
        else:
            method = "combined_weighted"
        
        return final_est, final_conf, method


def enhance_property_with_estimation(property_data: Dict, db_url: str) -> Dict:
    """Helper function to enhance property data with value estimation if needed"""
    if property_data.get('market_value', 0) == 0:
        estimator = PropertyValueEstimator(db_url)
        estimation = estimator.estimate_property_value(property_data)
        
        # Add estimation to property data
        property_data['value_estimation'] = estimation
        
        # Also set estimated value as market_value for compatibility
        if estimation['estimated'] and estimation['value'] > 0:
            property_data['estimated_market_value'] = estimation['value']
            property_data['estimation_confidence'] = estimation['confidence']
    
    return property_data