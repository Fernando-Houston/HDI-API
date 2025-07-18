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
import urllib.parse

# Use structlog if available, fallback to standard logging
try:
    logger = structlog.get_logger(__name__)
except:
    logger = logging.getLogger(__name__)

class PostgresHCADClient:
    """PostgreSQL-based HCAD client - replaces all web scraping"""

    def __init__(self):
        # Use Google Cloud SQL database with proper URL encoding
        db_url = os.getenv('DATABASE_URL')
        
        if db_url:
            # If DATABASE_URL is provided, use it directly
            self.db_url = db_url
        else:
            # Build URL with proper encoding
            password = urllib.parse.quote("JN#Fly/{;>p.bXVL")
            self.db_url = f"postgresql://postgres:{password}@34.135.126.23:5432/hcad"
        
        logger.info("PostgreSQL HCAD Client initialized with Google Cloud SQL")

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

                    if not result:
                        logger.info(f"No property found for address: {address}")
                        return None

                    # Convert to dict if needed
                    if hasattr(result, '_asdict'):
                        result = result._asdict()
                    else:
                        result = dict(result)

                    # Format response like old HCAD scraper
                    property_data = self._format_hcad_response(result)

                    # Add timing
                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"PostgreSQL query completed in {elapsed:.2f}s for {address}")

                    return property_data

        except Exception as e:
            logger.error(f"Database error for address {address}: {str(e)}")
            return None

    def _parse_address(self, address: str) -> Optional[Dict]:
        """Parse address into components"""
        # Match patterns like "1234 Main St" or "1234 N Main Street"
        pattern = r'^(\d+)\s+(.+?)(?:\s+(ST|STREET|AVE|AVENUE|RD|ROAD|DR|DRIVE|LN|LANE|BLVD|BOULEVARD|CT|COURT|PL|PLACE|WAY|CIR|CIRCLE|TRL|TRAIL))?\.?$'
        match = re.match(pattern, address.strip(), re.IGNORECASE)
        
        if match:
            return {
                'number': match.group(1),
                'street': match.group(2).strip(),
                'suffix': match.group(3) or ''
            }
        return None

    def _format_hcad_response(self, db_row: Dict) -> Dict:
        """Format database row to match old HCAD scraper response"""
        # Core property details
        property_data = {
            'account_number': db_row.get('account_number'),
            'owner_name': db_row.get('owner_name'),
            'property_address': db_row.get('property_address'),
            'mailing_address': db_row.get('mail_address'),
            'property_type': db_row.get('property_type'),
            'property_class': db_row.get('property_class'),
            'property_class_description': db_row.get('property_class_desc'),
            
            # Values
            'market_value': db_row.get('total_value', 0),
            'land_value': db_row.get('land_value', 0),
            'improvement_value': db_row.get('building_value', 0),
            'assessed_value': db_row.get('assessed_value', 0),
            
            # Land details
            'land_area_sqft': db_row.get('area_sqft', 0),
            'land_area_acres': db_row.get('area_acres', 0.0),
            
            # Building details
            'year_built': db_row.get('year_built'),
            'building_sqft': db_row.get('area_sqft', 0),  # Using area_sqft as building_sqft
            
            # Location
            'city': db_row.get('city', 'HOUSTON'),
            'state': db_row.get('state', 'TX'),
            'zip_code': db_row.get('zip'),
            
            # Geometry
            'has_geometry': db_row.get('has_geometry', False),
            'centroid': {
                'lat': db_row.get('centroid_lat'),
                'lon': db_row.get('centroid_lon')
            } if db_row.get('centroid_lat') else None,
            'geometry_wkt': db_row.get('geometry_wkt'),
            
            # Tax info (mock for now - would need separate table)
            'tax_year': 2024,
            'taxes': {
                'total_tax': db_row.get('total_value', 0) * 0.02,  # Estimate 2% tax rate
                'entities': []
            },
            
            # Status
            'property_status': 'Active',
            'last_updated': datetime.now().isoformat()
        }
        
        # Add any extra data
        if db_row.get('extra_data'):
            property_data['extra_data'] = db_row['extra_data']
        
        return property_data

    def search_by_account(self, account_number: str) -> Optional[Dict]:
        """Search by HCAD account number"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM properties 
                        WHERE account_number = %s 
                        LIMIT 1
                    """, (account_number,))
                    
                    result = cur.fetchone()
                    if result:
                        return self._format_hcad_response(dict(result))
                    return None
                    
        except Exception as e:
            logger.error(f"Error searching by account {account_number}: {str(e)}")
            return None

    def search_by_owner(self, owner_name: str, limit: int = 100) -> List[Dict]:
        """Search properties by owner name"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    search_pattern = f'%{owner_name.upper()}%'
                    
                    cur.execute("""
                        SELECT * FROM properties 
                        WHERE UPPER(owner_name) LIKE %s
                        ORDER BY total_value DESC
                        LIMIT %s
                    """, (search_pattern, limit))
                    
                    results = cur.fetchall()
                    return [self._format_hcad_response(dict(row)) for row in results]
                    
        except Exception as e:
            logger.error(f"Error searching by owner {owner_name}: {str(e)}")
            return []

    def search_by_value_range(self, min_value: float, max_value: float, 
                            city: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Search properties by value range"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if city:
                        cur.execute("""
                            SELECT * FROM properties 
                            WHERE total_value BETWEEN %s AND %s
                            AND UPPER(city) = %s
                            ORDER BY total_value DESC
                            LIMIT %s
                        """, (min_value, max_value, city.upper(), limit))
                    else:
                        cur.execute("""
                            SELECT * FROM properties 
                            WHERE total_value BETWEEN %s AND %s
                            ORDER BY total_value DESC
                            LIMIT %s
                        """, (min_value, max_value, limit))
                    
                    results = cur.fetchall()
                    return [self._format_hcad_response(dict(row)) for row in results]
                    
        except Exception as e:
            logger.error(f"Error searching by value range: {str(e)}")
            return []

    def get_properties_near_location(self, lat: float, lon: float, 
                                   radius_miles: float = 0.5, limit: int = 20) -> List[Dict]:
        """Get properties within radius of coordinates"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Calculate distance using PostgreSQL earthdistance
                    # Approximate: 1 degree = 69 miles
                    degree_radius = radius_miles / 69.0
                    
                    cur.execute("""
                        SELECT *,
                        SQRT(POW(centroid_lat - %s, 2) + POW(centroid_lon - %s, 2)) * 69 as distance_miles
                        FROM properties
                        WHERE centroid_lat IS NOT NULL 
                        AND centroid_lon IS NOT NULL
                        AND centroid_lat BETWEEN %s AND %s
                        AND centroid_lon BETWEEN %s AND %s
                        ORDER BY distance_miles
                        LIMIT %s
                    """, (
                        lat, lon,
                        lat - degree_radius, lat + degree_radius,
                        lon - degree_radius, lon + degree_radius,
                        limit
                    ))
                    
                    results = cur.fetchall()
                    formatted_results = []
                    
                    for row in results:
                        prop = self._format_hcad_response(dict(row))
                        prop['distance_miles'] = round(row['distance_miles'], 2)
                        formatted_results.append(prop)
                    
                    return formatted_results
                    
        except Exception as e:
            logger.error(f"Error searching near location: {str(e)}")
            return []

    def get_neighborhood_stats(self, city: str) -> Dict:
        """Get neighborhood statistics for a city"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as property_count,
                            AVG(total_value) as avg_value,
                            MIN(total_value) as min_value,
                            MAX(total_value) as max_value,
                            AVG(building_value) as avg_building_value,
                            AVG(land_value) as avg_land_value,
                            AVG(area_sqft) as avg_sqft,
                            COUNT(CASE WHEN year_built > 2020 THEN 1 END) as new_construction_count
                        FROM properties
                        WHERE UPPER(city) = %s
                        AND total_value > 0
                    """, (city.upper(),))
                    
                    stats = cur.fetchone()
                    
                    if stats:
                        return {
                            'city': city,
                            'property_count': stats['property_count'],
                            'average_value': round(stats['avg_value'], 2) if stats['avg_value'] else 0,
                            'min_value': stats['min_value'] or 0,
                            'max_value': stats['max_value'] or 0,
                            'avg_building_value': round(stats['avg_building_value'], 2) if stats['avg_building_value'] else 0,
                            'avg_land_value': round(stats['avg_land_value'], 2) if stats['avg_land_value'] else 0,
                            'avg_sqft': round(stats['avg_sqft'], 2) if stats['avg_sqft'] else 0,
                            'new_construction_count': stats['new_construction_count'] or 0
                        }
                    
                    return {'city': city, 'property_count': 0}
                    
        except Exception as e:
            logger.error(f"Error getting neighborhood stats: {str(e)}")
            return {'city': city, 'error': str(e)}

    def find_similar_properties(self, property_data: Dict, radius_miles: float = 1.0, 
                              limit: int = 20) -> List[Dict]:
        """Find properties similar to given property"""
        try:
            # Use property location if available
            if property_data.get('centroid_lat') and property_data.get('centroid_lon'):
                lat = property_data['centroid_lat']
                lon = property_data['centroid_lon']
            elif property_data.get('centroid'):
                lat = property_data['centroid'].get('lat')
                lon = property_data['centroid'].get('lon')
            else:
                # Can't find similar without location
                return []
            
            # Get nearby properties
            nearby = self.get_properties_near_location(lat, lon, radius_miles, limit * 2)
            
            # Filter for similar properties
            target_value = property_data.get('total_value', 0) or property_data.get('market_value', 0)
            target_sqft = property_data.get('area_sqft', 0) or property_data.get('building_sqft', 0)
            
            similar = []
            for prop in nearby:
                # Skip the same property
                if prop['account_number'] == property_data.get('account_number'):
                    continue
                
                # Check if similar (within 30% of value and size)
                prop_value = prop.get('market_value', 0)
                prop_sqft = prop.get('building_sqft', 0)
                
                if target_value > 0 and prop_value > 0:
                    value_diff = abs(prop_value - target_value) / target_value
                    if value_diff <= 0.3:  # Within 30%
                        prop['similarity_score'] = round((1 - value_diff) * 100, 1)
                        similar.append(prop)
                
                if len(similar) >= limit:
                    break
            
            # Sort by similarity score
            similar.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            return similar[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar properties: {str(e)}")
            return []

    def search_properties_by_address(self, query: str, limit: int = 10) -> List[Dict]:
        """Enhanced search with fuzzy matching and standardized response"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Clean the query
                    query_clean = query.strip().upper()
                    
                    # Stage 1: Try exact match first
                    cur.execute("""
                        SELECT * FROM properties 
                        WHERE UPPER(property_address) = %s
                        LIMIT %s
                    """, (query_clean, limit))
                    
                    results = cur.fetchall()
                    
                    # Stage 2: Try LIKE search if no exact match
                    if not results:
                        cur.execute("""
                            SELECT * FROM properties 
                            WHERE UPPER(property_address) LIKE %s
                            ORDER BY 
                                CASE 
                                    WHEN UPPER(property_address) LIKE %s THEN 1
                                    WHEN UPPER(property_address) LIKE %s THEN 2
                                    ELSE 3
                                END,
                                total_value DESC
                            LIMIT %s
                        """, (f'%{query_clean}%', f'{query_clean}%', f'%{query_clean}', limit))
                        
                        results = cur.fetchall()
                    
                    # Stage 3: Try component matching if still no results
                    if not results:
                        # Parse the query into components
                        words = query_clean.split()
                        if len(words) >= 2:
                            # Assume first word might be number, rest is street
                            number_part = words[0] if words[0].isdigit() else None
                            street_part = ' '.join(words[1:]) if len(words) > 1 else ' '.join(words)
                            
                            if number_part:
                                # Search with both number and street
                                cur.execute("""
                                    SELECT * FROM properties 
                                    WHERE UPPER(property_address) LIKE %s
                                    AND UPPER(property_address) LIKE %s
                                    ORDER BY total_value DESC
                                    LIMIT %s
                                """, (f'%{number_part}%', f'%{street_part}%', limit))
                            else:
                                # Just search for street name
                                cur.execute("""
                                    SELECT * FROM properties 
                                    WHERE UPPER(property_address) LIKE %s
                                    ORDER BY total_value DESC
                                    LIMIT %s
                                """, (f'%{street_part}%', limit))
                            
                            results = cur.fetchall()
                    
                    # Format results for frontend (camelCase)
                    formatted_results = []
                    for row in results:
                        prop = dict(row)
                        formatted_prop = self._format_property_for_frontend(prop)
                        formatted_results.append(formatted_prop)
                    
                    logger.info(f"Search '{query}' returned {len(formatted_results)} results")
                    return formatted_results
                    
        except Exception as e:
            logger.error(f"Search error for query '{query}': {str(e)}")
            return []
    
    def _format_property_for_frontend(self, prop: Dict) -> Dict:
        """Format property data for frontend consumption with camelCase"""
        # Calculate derived values
        market_value = prop.get('total_value', 0)
        building_sqft = prop.get('area_sqft', 0)
        year_built = prop.get('year_built')
        
        # Create investment score based on value and age
        investment_score = 50  # Base score
        if market_value > 0:
            if market_value < 200000:
                investment_score += 20  # Affordable entry
            elif market_value < 500000:
                investment_score += 15  # Mid-range
            else:
                investment_score += 10  # Higher-end
        
        if year_built:
            age = 2024 - year_built
            if age < 5:
                investment_score += 20  # New construction
            elif age < 20:
                investment_score += 10  # Relatively new
            elif age > 50:
                investment_score -= 10  # Older property
        
        # Determine neighborhood trend
        neighborhood_trend = "Stable"
        if market_value > 500000:
            neighborhood_trend = "Premium"
        elif market_value > 300000:
            neighborhood_trend = "Growing"
        elif market_value < 150000:
            neighborhood_trend = "Affordable"
        
        # Calculate rental estimate (rough estimate: 0.8% of property value per month)
        rental_estimate = int(market_value * 0.008) if market_value > 0 else 0
        
        # Create value range
        min_value = int(market_value * 0.9) if market_value > 0 else 0
        max_value = int(market_value * 1.1) if market_value > 0 else 0
        
        return {
            # Core identifiers
            'accountNumber': prop.get('account_number'),
            'address': prop.get('property_address'),
            'city': prop.get('city', 'HOUSTON'),
            'state': prop.get('state', 'TX'),
            'zip': prop.get('zip'),
            
            # Ownership
            'ownerName': prop.get('owner_name'),
            'mailingAddress': prop.get('mail_address'),
            
            # Property details
            'propertyType': prop.get('property_type'),
            'propertyClass': prop.get('property_class'),
            'yearBuilt': year_built,
            'squareFeet': building_sqft,
            'lotSize': prop.get('area_sqft', 0),
            'acres': prop.get('area_acres', 0),
            
            # Values
            'marketValue': market_value,
            'landValue': prop.get('land_value', 0),
            'improvementValue': prop.get('building_value', 0),
            'assessedValue': prop.get('assessed_value', 0),
            
            # Location data
            'latitude': prop.get('centroid_lat'),
            'longitude': prop.get('centroid_lon'),
            'hasGeometry': prop.get('has_geometry', False),
            
            # Frontend-specific fields with intelligent defaults
            'investmentScore': min(100, max(0, investment_score)),
            'neighborhoodTrend': neighborhood_trend,
            'estimatedValueRange': {
                'min': min_value,
                'max': max_value,
                'formatted': f"${min_value:,} - ${max_value:,}"
            },
            'rentalEstimate': rental_estimate,
            'pricePerSqft': int(market_value / building_sqft) if building_sqft > 0 else 0,
            
            # Additional metadata
            'lastUpdated': datetime.now().isoformat(),
            'dataSource': 'HCAD',
            'searchScore': 1.0  # Can be adjusted based on search relevance
        }