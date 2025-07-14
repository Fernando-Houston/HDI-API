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

    def close(self):
        """Compatibility method - PostgreSQL uses connection pooling"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()