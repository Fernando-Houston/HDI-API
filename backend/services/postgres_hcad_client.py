"""PostgreSQL-based HCAD client - replaces all web scraping"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Dict, Optional, List
import re
from datetime import datetime
import logging
import structlog
from backend.utils.cache import cached_property
from backend.services.value_estimator import enhance_property_with_estimation
from backend.utils.geometry import enhance_with_geometry_analysis
from backend.database.connection_pool import db_pool

# Use structlog if available, fallback to standard logging
try:
    logger = structlog.get_logger(__name__)
except:
    logger = logging.getLogger(__name__)

class PostgresHCADClient:
    """PostgreSQL-based HCAD client - replaces all web scraping"""

    def __init__(self):
        # Use environment variable or direct connection string
        self.db_url = os.getenv('DATABASE_URL',
            "postgresql://postgres:JtJbPAybwWfYvRCgIlKWakPutHuggUoN@caboose.proxy.rlwy.net:21434/railway")
        logger.info("PostgreSQL HCAD Client initialized")

    @cached_property(ttl_seconds=3600)  # Cache for 1 hour
    def get_property_data(self, address: str) -> Optional[Dict]:
        """
        Get property data from PostgreSQL database
        Returns in same format as old HCAD scraper for compatibility
        """
        try:
            start_time = datetime.now()

            with db_pool.get_cursor() as cur:
                    # Clean the address
                    address_clean = address.strip().upper()

                    # First try exact match
                    query = """
                    SELECT 
                        account_number,
                        owner_name,
                        property_address,
                        city,
                        state,
                        zip,
                        property_type,
                        property_class,
                        property_class_desc,
                        land_value,
                        building_value,
                        total_value,
                        assessed_value,
                        area_sqft,
                        area_acres,
                        year_built,
                        has_geometry,
                        centroid_lat,
                        centroid_lon,
                        geometry_wkt,
                        bbox_minx,
                        bbox_miny,
                        bbox_maxx,
                        bbox_maxy,
                        mail_address,
                        mail_city,
                        mail_state,
                        mail_zip,
                        extra_data
                    FROM properties
                    WHERE UPPER(property_address) LIKE %(search_pattern)s
                    LIMIT 1
                    """

                    # Try with wildcards - using format to avoid parameterization issues
                    search_pattern = f'%{address_clean}%'
                    cur.execute(query.format(search_pattern=search_pattern), {'search_pattern': search_pattern})
                    result = cur.fetchone()

                    # If no exact match, try parsing
                    if not result:
                        parts = self._parse_address(address)
                        if parts:
                            query_parsed = """
                            SELECT * FROM properties
                            WHERE property_address LIKE %s
                            AND property_address LIKE %s
                            LIMIT 1
                            """
                            cur.execute(query_parsed,
                                      (f'{parts["number"]}%',
                                       f'%{parts["street"].upper()}%'))
                            result = cur.fetchone()

                    if result:
                        response_time = (datetime.now() - start_time).total_seconds()
                        logger.info(f"Found property in {response_time:.3f}s: {result['account_number']}")
                        formatted_response = self._format_hcad_response(dict(result))
                        
                        # Enhance with value estimation if needed
                        if formatted_response.get('market_value', 0) == 0:
                            formatted_response = enhance_property_with_estimation(formatted_response, self.db_url)
                        
                        # Enhance with geometry analysis
                        formatted_response = enhance_with_geometry_analysis(formatted_response)
                        
                        return formatted_response

                    logger.warning(f"No property found for address: {address}")
                    return None

        except Exception as e:
            logger.error(f"PostgreSQL error: {str(e)}")
            return None

    def get_property_by_address(self, address: str) -> Optional[Dict]:
        """Alias for get_property_data to match old interface"""
        return self.get_property_data(address)

    def _format_hcad_response(self, data: Dict) -> Dict:
        """Format database response to match expected HCAD format"""
        # Extract exemptions from extra_data if available
        extra_data = data.get('extra_data', {}) or {}
        exemptions = extra_data.get('exemptions', [])
        exemption_value = sum(e.get('amount', 0) for e in exemptions if isinstance(e, dict))

        return {
            # Core identification
            "account_number": data.get("account_number", ""),
            "owner_name": data.get("owner_name", ""),
            "property_address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": data.get("state", "TX"),
            "zip": data.get("zip", ""),

            # Mailing address
            "mailing_address": {
                "address": data.get("mail_address", ""),
                "city": data.get("mail_city", ""),
                "state": data.get("mail_state", ""),
                "zip": data.get("mail_zip", "")
            },

            # Values - ensure they're floats, handle NULLs properly
            "market_value": float(data.get("total_value") or 0),
            "appraised_value": float(data.get("assessed_value") or 0),
            "land_value": float(data.get("land_value") or 0),
            "improvement_value": float(data.get("building_value") or 0),
            "total_value": float(data.get("total_value") or 0),
            "exemption_value": exemption_value,

            # Property details
            "property_type": data.get("property_type", ""),
            "property_class": data.get("property_class", ""),
            "property_class_description": data.get("property_class_desc", ""),
            "building_sqft": float(data.get("area_sqft") or 0),
            "land_sqft": float(data.get("area_sqft") or 0),
            "living_sqft": float(data.get("area_sqft") or 0),  # Alias for compatibility
            "land_acres": float(data.get("area_acres") or 0),
            "year_built": int(data.get("year_built") or 0) if data.get("year_built") else None,

            # Location data
            "has_geometry": data.get("has_geometry", False),
            "latitude": float(data.get("centroid_lat")) if data.get("centroid_lat") else None,
            "longitude": float(data.get("centroid_lon")) if data.get("centroid_lon") else None,
            
            # Geometry data for mapping
            "geometry": {
                "wkt": data.get("geometry_wkt"),
                "centroid": {
                    "lat": float(data.get("centroid_lat")) if data.get("centroid_lat") else None,
                    "lon": float(data.get("centroid_lon")) if data.get("centroid_lon") else None
                },
                "bbox": {
                    "minX": float(data.get("bbox_minx")) if data.get("bbox_minx") else None,
                    "minY": float(data.get("bbox_miny")) if data.get("bbox_miny") else None,
                    "maxX": float(data.get("bbox_maxx")) if data.get("bbox_maxx") else None,
                    "maxY": float(data.get("bbox_maxy")) if data.get("bbox_maxy") else None
                }
            },

            # Additional data
            "legal_description": extra_data.get("legal_description", ""),
            "neighborhood": extra_data.get("neighborhood", ""),
            "subdivision": extra_data.get("subdivision", ""),

            # Tax data (if available in extra_data)
            "tax_rate": extra_data.get("tax_rate", 0),
            "taxes": extra_data.get("taxes", {}),
            "exemptions": exemptions,

            # Metadata
            "data_source": "PostgreSQL Database",
            "search_address": data.get("property_address", ""),
            "retrieved_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

    def _parse_address(self, address: str) -> Optional[Dict]:
        """Parse address into street number and name"""
        # Handle formats like "4118 Ella Blvd Houston TX 77018"
        match = re.match(r'^(\d+)\s+(.+?)(?:\s+(?:HOUSTON|KATY|SUGAR LAND|TX|TEXAS).*)?',
                        address.strip(), re.IGNORECASE)
        if match:
            return {
                'number': match.group(1),
                'street': match.group(2).strip()
            }
        return None

    # NEW POWERFUL METHODS NOW POSSIBLE WITH DATABASE!

    def search_by_owner(self, owner_name: str, limit: int = 100) -> List[Dict]:
        """Search all properties by owner name"""
        try:
            with db_pool.get_cursor() as cur:
                    query = """
                    SELECT * FROM properties
                    WHERE UPPER(owner_name) LIKE UPPER(%s)
                    ORDER BY total_value DESC
                    LIMIT %s
                    """
                    cur.execute(query, (f'%{owner_name}%', limit))
                    results = cur.fetchall()
                    return [self._format_hcad_response(dict(row)) for row in results]
        except Exception as e:
            logger.error(f"Owner search error: {str(e)}")
            return []

    def search_by_value_range(self, min_value: float, max_value: float, 
                             city: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Find properties within a value range"""
        try:
            with db_pool.get_cursor() as cur:
                    if city:
                        query = """
                        SELECT * FROM properties
                        WHERE total_value BETWEEN %s AND %s
                        AND UPPER(city) = UPPER(%s)
                        AND property_type LIKE '%Real Property%'
                        ORDER BY total_value DESC
                        LIMIT %s
                        """
                        cur.execute(query, (min_value, max_value, city, limit))
                    else:
                        query = """
                        SELECT * FROM properties
                        WHERE total_value BETWEEN %s AND %s
                        AND property_type LIKE '%Real Property%'
                        ORDER BY total_value DESC
                        LIMIT %s
                        """
                        cur.execute(query, (min_value, max_value, limit))

                    results = cur.fetchall()
                    return [self._format_hcad_response(dict(row)) for row in results]
        except Exception as e:
            logger.error(f"Value range search error: {str(e)}")
            return []
    
    def find_similar_properties(self, property_data: Dict, 
                               radius_miles: float = 1.0, 
                               limit: int = 20) -> List[Dict]:
        """Find similar properties within radius (default 1 mile, max 20 results)"""
        try:
            lat = property_data.get('latitude') or property_data.get('geometry', {}).get('centroid', {}).get('lat')
            lon = property_data.get('longitude') or property_data.get('geometry', {}).get('centroid', {}).get('lon')
            property_type = property_data.get('property_type', '')
            value = property_data.get('market_value', 0)
            sqft = property_data.get('building_sqft', 0)
            
            if not lat or not lon:
                logger.warning("No location data for similar property search")
                return []
            
            with db_pool.get_cursor() as cur:
                    # Find properties within radius with similar characteristics
                    query = """
                    SELECT 
                        *,
                        (3959 * acos(cos(radians(%s)) * cos(radians(centroid_lat)) * 
                         cos(radians(centroid_lon) - radians(%s)) + 
                         sin(radians(%s)) * sin(radians(centroid_lat)))) AS distance_miles
                    FROM properties
                    WHERE centroid_lat IS NOT NULL
                    AND centroid_lon IS NOT NULL
                    AND property_type = %s
                    AND account_number != %s
                    AND (3959 * acos(cos(radians(%s)) * cos(radians(centroid_lat)) * 
                         cos(radians(centroid_lon) - radians(%s)) + 
                         sin(radians(%s)) * sin(radians(centroid_lat)))) <= %s
                    """
                    
                    # Add value similarity if property has value
                    if value > 0:
                        query += " AND total_value BETWEEN %s AND %s"
                        value_range = (value * 0.8, value * 1.2)  # Within 20% of value
                    else:
                        value_range = ()
                    
                    # Add size similarity if available
                    if sqft > 0:
                        query += " AND area_sqft BETWEEN %s AND %s"
                        size_range = (sqft * 0.8, sqft * 1.2)  # Within 20% of size
                    else:
                        size_range = ()
                    
                    query += " ORDER BY distance_miles LIMIT %s"
                    
                    # Build parameters
                    params = [lat, lon, lat, property_type, property_data.get('account_number', ''), 
                             lat, lon, lat, radius_miles]
                    params.extend(value_range)
                    params.extend(size_range)
                    params.append(limit)
                    
                    cur.execute(query, params)
                    results = cur.fetchall()
                    
                    # Format and calculate similarity scores
                    similar_properties = []
                    for row in results:
                        prop = self._format_hcad_response(dict(row))
                        
                        # Calculate similarity score
                        similarity_score = self._calculate_similarity(property_data, prop, row['distance_miles'])
                        prop['similarity'] = {
                            'score': similarity_score,
                            'distance_miles': round(row['distance_miles'], 2),
                            'value_difference': prop.get('market_value', 0) - value if value > 0 else None,
                            'size_difference': prop.get('building_sqft', 0) - sqft if sqft > 0 else None
                        }
                        
                        similar_properties.append(prop)
                    
                    # Sort by similarity score
                    similar_properties.sort(key=lambda x: x['similarity']['score'], reverse=True)
                    
                    return similar_properties
                    
        except Exception as e:
            logger.error(f"Similar properties search error: {str(e)}")
            return []
    
    def _calculate_similarity(self, prop1: Dict, prop2: Dict, distance: float) -> float:
        """Calculate similarity score between two properties (0-1)"""
        score = 1.0
        
        # Distance factor (closer is better)
        distance_penalty = min(distance / 2.0, 0.5)  # Max 0.5 penalty for distance
        score -= distance_penalty
        
        # Value similarity (if both have values)
        val1 = prop1.get('market_value', 0)
        val2 = prop2.get('market_value', 0)
        if val1 > 0 and val2 > 0:
            value_diff_pct = abs(val1 - val2) / max(val1, val2)
            score -= value_diff_pct * 0.3  # Max 0.3 penalty for value difference
        
        # Size similarity (if both have sizes)
        size1 = prop1.get('building_sqft', 0)
        size2 = prop2.get('building_sqft', 0)
        if size1 > 0 and size2 > 0:
            size_diff_pct = abs(size1 - size2) / max(size1, size2)
            score -= size_diff_pct * 0.2  # Max 0.2 penalty for size difference
        
        return max(0, min(1, score))  # Clamp to 0-1

    def get_neighborhood_stats(self, city: str) -> Dict:
        """Get aggregate statistics for a city/neighborhood"""
        try:
            with db_pool.get_cursor() as cur:
                    query = """
                    SELECT 
                        COUNT(*) as property_count,
                        AVG(total_value) as avg_value,
                        MIN(total_value) as min_value,
                        MAX(total_value) as max_value,
                        SUM(area_acres) as total_acres,
                        AVG(CASE WHEN year_built > 0 THEN year_built END) as avg_year_built
                    FROM properties
                    WHERE UPPER(city) = UPPER(%s)
                    AND property_type LIKE '%Real Property%'
                    AND total_value > 0
                    """
                    cur.execute(query, (city,))
                    result = cur.fetchone()
                    
                    if result:
                        # Convert to regular dict and handle None values
                        stats = dict(result)
                        return {
                            "property_count": int(stats.get("property_count", 0)),
                            "avg_value": float(stats.get("avg_value", 0) or 0),
                            "min_value": float(stats.get("min_value", 0) or 0),
                            "max_value": float(stats.get("max_value", 0) or 0),
                            "total_acres": float(stats.get("total_acres", 0) or 0),
                            "avg_year_built": int(stats.get("avg_year_built", 0) or 0) if stats.get("avg_year_built") else None
                        }
                    return {}
        except Exception as e:
            logger.error(f"Neighborhood stats error: {str(e)}")
            return {}

    def search_by_account(self, account_number: str) -> Optional[Dict]:
        """Search property by account number"""
        try:
            with db_pool.get_cursor() as cur:
                    query = """
                    SELECT * FROM properties
                    WHERE account_number = %s
                    LIMIT 1
                    """
                    cur.execute(query, (account_number,))
                    result = cur.fetchone()
                    
                    if result:
                        return self._format_hcad_response(dict(result))
                    return None
        except Exception as e:
            logger.error(f"Account search error: {str(e)}")
            return None

    def get_properties_near_location(self, lat: float, lon: float, radius_miles: float = 0.5, limit: int = 20) -> List[Dict]:
        """Get properties within radius of a location (requires geometry data)"""
        try:
            with db_pool.get_cursor() as cur:
                    # Using simple distance calculation
                    # For more accuracy, use PostGIS extensions
                    query = """
                    SELECT *,
                        (3959 * acos(cos(radians(%s)) * cos(radians(centroid_lat)) * 
                         cos(radians(centroid_lon) - radians(%s)) + 
                         sin(radians(%s)) * sin(radians(centroid_lat)))) as distance
                    FROM properties
                    WHERE has_geometry = true
                    AND centroid_lat IS NOT NULL
                    AND centroid_lon IS NOT NULL
                    AND (3959 * acos(cos(radians(%s)) * cos(radians(centroid_lat)) * 
                         cos(radians(centroid_lon) - radians(%s)) + 
                         sin(radians(%s)) * sin(radians(centroid_lat)))) < %s
                    ORDER BY distance
                    LIMIT %s
                    """
                    cur.execute(query, (lat, lon, lat, lat, lon, lat, radius_miles, limit))
                    results = cur.fetchall()
                    
                    formatted_results = []
                    for row in results:
                        prop = self._format_hcad_response(dict(row))
                        prop['distance_miles'] = round(row['distance'], 2)
                        formatted_results.append(prop)
                    
                    return formatted_results
        except Exception as e:
            logger.error(f"Location search error: {str(e)}")
            return []

    def search_properties_by_address(self, address: str, limit: int = 20) -> List[Dict]:
        """
        Enhanced address search that returns multiple properties with fuzzy matching
        Returns standardized camelCase format with all required frontend fields
        """
        try:
            # Use direct connection instead of pool to debug
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Clean the address for better matching
                    address_clean = address.strip().upper()
                    
                    # Simplified query first - just search in property_address
                    query = """
                    SELECT * FROM properties
                    WHERE UPPER(property_address) LIKE %s
                    ORDER BY total_value DESC NULLS LAST
                    LIMIT %s
                    """
                    
                    search_pattern = f'%{address_clean}%'
                    cur.execute(query, (search_pattern, limit))
                    exact_matches = cur.fetchall()
                    
                    results = []
                    
                    # Process results
                    for row in exact_matches:
                        try:
                            formatted_prop = self._format_property_for_frontend(dict(row))
                            results.append(formatted_prop)
                        except Exception as format_error:
                            logger.warning(f"Failed to format property {row.get('account_number', 'unknown')}: {format_error}")
                            continue
                    
                    # If no results and address has components, try fuzzy matching
                    if len(results) == 0:
                        address_parts = self._parse_address_components(address)
                        if address_parts and address_parts.get('number') and address_parts.get('street'):
                            # Try searching by components
                            fuzzy_query = """
                            SELECT * FROM properties
                            WHERE property_address LIKE %s
                            AND property_address LIKE %s
                            ORDER BY total_value DESC NULLS LAST
                            LIMIT %s
                            """
                            
                            street_number_pattern = f'{address_parts["number"]}%'
                            street_name_pattern = f'%{address_parts["street"].upper()}%'
                            
                            cur.execute(fuzzy_query, (street_number_pattern, street_name_pattern, limit))
                            fuzzy_matches = cur.fetchall()
                            
                            for row in fuzzy_matches:
                                try:
                                    formatted_prop = self._format_property_for_frontend(dict(row))
                                    results.append(formatted_prop)
                                except Exception as format_error:
                                    logger.warning(f"Failed to format property {row.get('account_number', 'unknown')}: {format_error}")
                                    continue
                    
                    logger.info(f"Address search found {len(results)} properties for: {address}")
                    return results
                
        except Exception as e:
            logger.error(f"Enhanced address search error: {type(e).__name__}: {str(e)}")
            return []
    
    def _parse_address_components(self, address: str) -> Optional[Dict]:
        """Enhanced address parsing with better component extraction"""
        import re
        
        # Remove common suffixes and normalize
        address_clean = re.sub(r'\s+(HOUSTON|TX|TEXAS|\d{5})\s*$', '', address.strip(), flags=re.IGNORECASE)
        
        # Extract street number and name
        patterns = [
            r'^(\d+)\s+(.+?)(?:\s+(?:APT|UNIT|STE|#).*)?$',  # With apt/unit
            r'^(\d+)\s+(.+)$'  # Basic pattern
        ]
        
        for pattern in patterns:
            match = re.match(pattern, address_clean.strip(), re.IGNORECASE)
            if match:
                return {
                    'number': match.group(1),
                    'street': match.group(2).strip()
                }
        
        return None
    
    def _format_property_for_frontend(self, data: Dict) -> Dict:
        """Format property data for frontend with all required fields in camelCase"""
        # Get base formatted data
        base_data = self._format_hcad_response(data)
        
        # Extract key values
        market_value = base_data.get('market_value', 0)
        building_sqft = base_data.get('building_sqft', 0)
        year_built = base_data.get('year_built', 0)
        
        # Calculate derived values
        price_per_sqft = (market_value / building_sqft) if building_sqft > 0 else 0
        
        # Generate default AI-derived fields (these would normally come from AI services)
        estimated_rental = self._estimate_rental_value(market_value, building_sqft, base_data.get('city', ''))
        investment_score = self._calculate_investment_score(market_value, year_built, base_data.get('property_type', ''))
        neighborhood_trend = self._get_default_neighborhood_trend(base_data.get('city', ''))
        estimated_value_range = self._calculate_value_range(market_value)
        
        # Return frontend-compatible format with all required fields
        return {
            # Core property information (camelCase)
            "accountNumber": base_data.get('account_number', ''),
            "address": base_data.get('property_address', ''),
            "city": base_data.get('city', ''),
            "state": base_data.get('state', 'TX'),
            "zipCode": base_data.get('zip', ''),
            "ownerName": base_data.get('owner_name', ''),
            
            # Property details
            "propertyType": base_data.get('property_type', ''),
            "propertyClass": base_data.get('property_class', ''),
            "yearBuilt": year_built,
            "buildingSqft": building_sqft,
            "landSqft": base_data.get('land_sqft', 0),
            "landAcres": base_data.get('land_acres', 0),
            
            # Financial information
            "marketValue": market_value,
            "appraisedValue": base_data.get('appraised_value', 0),
            "landValue": base_data.get('land_value', 0),
            "improvementValue": base_data.get('improvement_value', 0),
            "pricePerSqft": round(price_per_sqft, 2),
            
            # Location data
            "latitude": base_data.get('latitude'),
            "longitude": base_data.get('longitude'),
            "hasGeometry": base_data.get('has_geometry', False),
            
            # Required AI-derived fields with defaults
            "neighborhoodTrend": neighborhood_trend,
            "estimatedValueRange": estimated_value_range,
            "rentalEstimate": estimated_rental,
            "investmentScore": investment_score,
            
            # Additional analysis fields
            "lastUpdated": base_data.get('last_updated', datetime.now().isoformat()),
            "dataSource": "PostgreSQL Database",
            "confidence": 0.8  # Default confidence score
        }
    
    def _estimate_rental_value(self, market_value: float, sqft: float, city: str) -> Dict:
        """Generate default rental estimate based on market value"""
        if market_value <= 0:
            return {"monthly": 0, "annual": 0, "confidence": "low"}
        
        # Use industry rule of thumb: monthly rent = 0.5-1% of market value
        base_monthly = market_value * 0.007  # 0.7% as middle ground
        
        # Adjust based on city and property size
        city_multiplier = 1.1 if city.upper() in ['HOUSTON', 'KATY', 'SUGAR LAND'] else 1.0
        size_multiplier = 1.05 if sqft > 2000 else 0.95 if sqft < 1000 else 1.0
        
        monthly_estimate = base_monthly * city_multiplier * size_multiplier
        
        return {
            "monthly": round(monthly_estimate),
            "annual": round(monthly_estimate * 12),
            "confidence": "medium"
        }
    
    def _calculate_investment_score(self, market_value: float, year_built: int, property_type: str) -> Dict:
        """Calculate default investment score"""
        score = 50  # Base score
        
        # Age factor
        current_year = datetime.now().year
        if year_built and year_built > 0:
            age = current_year - year_built
            if age < 10:
                score += 20
            elif age < 30:
                score += 10
            elif age > 50:
                score -= 10
        
        # Value factor
        if market_value > 500000:
            score += 15
        elif market_value < 150000:
            score -= 10
        
        # Property type factor
        if 'SINGLE FAMILY' in property_type.upper():
            score += 10
        elif 'CONDO' in property_type.upper():
            score += 5
        
        # Clamp score between 0-100
        final_score = max(0, min(100, score))
        
        # Determine rating
        if final_score >= 80:
            rating = "excellent"
        elif final_score >= 70:
            rating = "good"
        elif final_score >= 50:
            rating = "fair"
        else:
            rating = "poor"
        
        return {
            "score": final_score,
            "rating": rating,
            "factors": ["age", "value", "type"]
        }
    
    def _get_default_neighborhood_trend(self, city: str) -> Dict:
        """Generate default neighborhood trend data"""
        # Default trends for major Houston areas
        default_trends = {
            "HOUSTON": {"direction": "up", "percentage": 3.5, "period": "12_months"},
            "KATY": {"direction": "up", "percentage": 4.2, "period": "12_months"},
            "SUGAR LAND": {"direction": "up", "percentage": 3.8, "period": "12_months"},
            "CYPRESS": {"direction": "up", "percentage": 3.2, "period": "12_months"}
        }
        
        city_upper = city.upper()
        if city_upper in default_trends:
            return default_trends[city_upper]
        else:
            return {"direction": "stable", "percentage": 2.0, "period": "12_months"}
    
    def _calculate_value_range(self, market_value: float) -> Dict:
        """Calculate estimated value range around market value"""
        if market_value <= 0:
            return {"min": 0, "max": 0, "confidence": "low"}
        
        # Use +/- 10% as standard range
        range_percentage = 0.10
        min_value = market_value * (1 - range_percentage)
        max_value = market_value * (1 + range_percentage)
        
        return {
            "min": round(min_value),
            "max": round(max_value),
            "confidence": "medium"
        }

    def search_properties_by_address(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Enhanced search for multiple properties with fuzzy matching
        Returns array of properties with standardized format
        """
        if not query.strip():
            return []
            
        query = query.strip().upper()
        
        try:
            with db_pool.get_cursor() as cur:
                results = []
                
                # Stage 1: Exact match
                cur.execute("""
                    SELECT * FROM properties 
                    WHERE property_address = %s
                    LIMIT %s
                """, (query, limit))
                exact_matches = cur.fetchall()
                
                if exact_matches:
                    results.extend([self._format_property_for_frontend(dict(row)) for row in exact_matches])
                
                # Stage 2: LIKE match if we need more results
                if len(results) < limit:
                    remaining = limit - len(results)
                    cur.execute("""
                        SELECT * FROM properties 
                        WHERE property_address LIKE %s
                        AND property_address != %s
                        ORDER BY LENGTH(property_address), property_address
                        LIMIT %s
                    """, (f'%{query}%', query, remaining))
                    like_matches = cur.fetchall()
                    results.extend([self._format_property_for_frontend(dict(row)) for row in like_matches])
                
                # Stage 3: Component matching if still need more
                if len(results) < limit and len(query.split()) > 1:
                    remaining = limit - len(results)
                    components = query.split()
                    
                    # Try matching on individual components
                    component_conditions = []
                    params = []
                    for comp in components:
                        if len(comp) >= 3:  # Only meaningful components
                            component_conditions.append("property_address LIKE %s")
                            params.append(f'%{comp}%')
                    
                    if component_conditions:
                        existing_addresses = [r['address'] for r in results]
                        
                        if existing_addresses:
                            placeholders = ','.join(['%s'] * len(existing_addresses))
                            component_query = f"""
                                SELECT * FROM properties 
                                WHERE ({' AND '.join(component_conditions)})
                                AND property_address NOT IN ({placeholders})
                                ORDER BY LENGTH(property_address), property_address
                                LIMIT %s
                            """
                            params.extend(existing_addresses)
                        else:
                            component_query = f"""
                                SELECT * FROM properties 
                                WHERE ({' AND '.join(component_conditions)})
                                ORDER BY LENGTH(property_address), property_address
                                LIMIT %s
                            """
                        
                        params.append(remaining)
                        cur.execute(component_query, params)
                        component_matches = cur.fetchall()
                        results.extend([self._format_property_for_frontend(dict(row)) for row in component_matches])
                
                return results[:limit]
                
        except Exception as e:
            logger.error(f"Error in enhanced search: {str(e)}")
            return []

    def _format_property_for_frontend(self, property_data: Dict) -> Dict:
        """
        Format property data with all required frontend fields in camelCase
        """
        # Get base HCAD response format
        base_response = self._format_hcad_response(property_data)
        
        # Convert to camelCase and add missing fields
        formatted = {
            # Core property information (camelCase)
            "accountNumber": base_response.get("account_number", ""),
            "address": base_response.get("property_address", ""),
            "ownerName": base_response.get("owner_name", ""),
            "city": base_response.get("city", ""),
            "zipCode": base_response.get("zip_code", ""),
            "propertyType": base_response.get("property_type", "residential"),
            
            # Financial information
            "marketValue": base_response.get("market_value", 0),
            "landValue": base_response.get("land_value", 0),
            "improvementValue": base_response.get("improvement_value", 0),
            "totalValue": base_response.get("total_value", 0),
            
            # Physical characteristics
            "squareFeet": base_response.get("building_sqft", 0),
            "areaSqft": base_response.get("area_sqft", 0),
            "yearBuilt": base_response.get("year_built"),
            "lotSize": base_response.get("lot_size", 0),
            
            # Location data
            "latitude": base_response.get("latitude"),
            "longitude": base_response.get("longitude"),
            
            # Geometry information (if available)
            "geometry": base_response.get("geometry", {}),
            
            # Required frontend fields with defaults
            "estimatedValueRange": self._calculate_value_range(base_response.get("market_value", 0)),
            "rentalEstimate": self._calculate_rental_estimate(base_response.get("market_value", 0)),
            "investmentScore": self._calculate_investment_score(property_data),
            "neighborhoodTrend": self._get_default_neighborhood_trend(base_response.get("city", "Houston")),
            
            # Additional metadata
            "lastUpdated": base_response.get("last_updated"),
            "dataSource": "hcad_postgresql",
            "searchRelevance": 1.0  # Can be updated based on search matching
        }
        
        return formatted

    def _calculate_rental_estimate(self, market_value: float) -> Dict:
        """Calculate rental estimate using industry standard ratios"""
        if market_value <= 0:
            return {"monthly": 0, "annual": 0, "confidence": "low"}
        
        # Industry rule of thumb: 0.7% - 1% of property value per month
        monthly_rate = 0.007  # 0.7%
        monthly_rent = market_value * monthly_rate
        annual_rent = monthly_rent * 12
        
        return {
            "monthly": round(monthly_rent),
            "annual": round(annual_rent),
            "confidence": "medium",
            "source": "calculated"
        }

    def close(self):
        """Compatibility method - PostgreSQL uses connection pooling"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()