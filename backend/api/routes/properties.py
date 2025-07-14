"""Property data endpoints with HCAD integration"""

from flask import request
from flask_restx import Namespace, Resource, fields
import os
import structlog
from datetime import datetime

from backend.services.data_fusion import DataFusionEngine
from backend.services.postgres_hcad_client import PostgresHCADClient
from backend.services.perplexity_client import PerplexityClient
from backend.utils.exceptions import ValidationError

logger = structlog.get_logger(__name__)

properties_ns = Namespace("properties", description="Property data operations")

# Request/Response models
property_search_model = properties_ns.model("PropertySearch", {
    "address": fields.String(required=True, description="Property address"),
    "limit": fields.Integer(default=20, description="Maximum number of results to return"),
    "include_market_data": fields.Boolean(default=True, description="Include market analysis"),
    "include_comparables": fields.Boolean(default=False, description="Include comparable properties")
})

property_response_model = properties_ns.model("PropertyResponse", {
    "address": fields.String(description="Property address"),
    "official_data": fields.Raw(description="HCAD official data"),
    "market_insights": fields.Raw(description="Market analysis"),
    "combined_analysis": fields.Raw(description="Combined insights"),
    "recommendations": fields.List(fields.String, description="Actionable recommendations"),
    "confidence_score": fields.Float(description="Data confidence score (0-1)"),
    "sources": fields.Raw(description="Data sources used"),
    "timestamp": fields.String(description="Response timestamp")
})

@properties_ns.route("/search")
class PropertySearch(Resource):
    """Enhanced property search endpoint that returns arrays"""
    
    @properties_ns.doc("search_properties")
    @properties_ns.expect(property_search_model)
    def post(self):
        """Search for properties by address with fuzzy matching and standardized response"""
        data = request.get_json()
        
        if not data or "address" not in data:
            raise ValidationError("Address is required")
        
        address = data["address"]
        limit = data.get("limit", 20)  # Default to 20 results
        
        try:
            # Use enhanced PostgreSQL search
            hcad_client = PostgresHCADClient()
            properties = hcad_client.search_properties_by_address(address, limit=limit)
            
            # Build standardized response
            response = {
                "success": True,
                "query": address,
                "count": len(properties),
                "properties": properties,
                "timestamp": datetime.now().isoformat(),
                "searchType": "address_fuzzy_match"
            }
            
            logger.info(f"Search returned {len(properties)} properties for address: {address}")
            return response
            
        except Exception as e:
            logger.error(f"Search failed for address {address}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": address,
                "count": 0,
                "properties": [],
                "timestamp": datetime.now().isoformat()
            }, 500

@properties_ns.route("/search/address")
class AddressSearch(Resource):
    """GET endpoint for simple address search"""
    
    @properties_ns.doc("search_by_address",
        params={
            'q': 'Search query (address)',
            'limit': 'Maximum results (default: 20)',
        })
    def get(self):
        """Search properties by address using GET request"""
        query = request.args.get('q', '').strip()
        limit = min(request.args.get('limit', 20, type=int), 100)  # Max 100 results
        
        if not query:
            raise ValidationError("Query parameter 'q' is required")
        
        try:
            # Use enhanced PostgreSQL search
            hcad_client = PostgresHCADClient()
            properties = hcad_client.search_properties_by_address(query, limit=limit)
            
            # Build standardized response
            response = {
                "success": True,
                "query": query,
                "count": len(properties),
                "properties": properties,
                "timestamp": datetime.now().isoformat(),
                "searchType": "address_fuzzy_match"
            }
            
            logger.info(f"GET search returned {len(properties)} properties for query: {query}")
            return response
            
        except Exception as e:
            logger.error(f"GET search failed for query {query}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "count": 0,
                "properties": [],
                "timestamp": datetime.now().isoformat()
            }, 500

@properties_ns.route("/analyze")
class PropertyAnalysis(Resource):
    """Property analysis endpoint"""
    
    @properties_ns.doc("analyze_property")
    @properties_ns.param("address", "Property address", required=True)
    @properties_ns.marshal_with(property_response_model)
    def get(self):
        """Analyze a specific property"""
        address = request.args.get("address")
        
        if not address:
            raise ValidationError("Address parameter is required")
        
        # Initialize data fusion engine
        fusion = DataFusionEngine()
        
        # Get property intelligence
        intelligence = fusion.get_property_intelligence(address)
        
        return intelligence

@properties_ns.route("/hcad/<string:account_number>")
class HCADProperty(Resource):
    """Direct HCAD property lookup"""
    
    @properties_ns.doc("get_hcad_property")
    def get(self, account_number):
        """Get property details by HCAD account number"""
        hcad_client = PostgresHCADClient()
        
        try:
            details = hcad_client.search_by_account(account_number)
            if details:
                return {
                    "success": True,
                    "data": details,
                    "account_number": account_number
                }
            else:
                return {
                    "success": False,
                    "error": "Property not found",
                    "account_number": account_number
                }, 404
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "account_number": account_number
            }, 500


# NEW POWERFUL ENDPOINTS

@properties_ns.route('/owner/<string:owner_name>')
class PropertyOwnerSearch(Resource):
    """Search properties by owner name"""
    
    @properties_ns.doc("search_by_owner")
    def get(self, owner_name):
        """Find all properties owned by a person/entity"""
        hcad_client = PostgresHCADClient()
        perplexity_client = PerplexityClient()
        
        # Get limit from query params
        limit = request.args.get('limit', 100, type=int)
        
        properties = hcad_client.search_by_owner(owner_name, limit=limit)

        # Enhance with Perplexity data for top properties
        if properties and len(properties) <= 5:
            for prop in properties[:5]:
                try:
                    perplexity_data = perplexity_client.query(
                        f"Property analysis for {prop['property_address']} Houston TX"
                    )
                    if perplexity_data.get('success'):
                        prop['market_analysis'] = perplexity_data.get('data')
                except:
                    pass

        return {
            "owner": owner_name,
            "property_count": len(properties),
            "total_value": sum(p['market_value'] for p in properties),
            "total_land_value": sum(p['land_value'] for p in properties),
            "total_improvement_value": sum(p['improvement_value'] for p in properties),
            "properties": properties
        }


# Value range search model
value_range_model = properties_ns.model("ValueRangeSearch", {
    "min_value": fields.Float(required=True, description="Minimum property value"),
    "max_value": fields.Float(required=True, description="Maximum property value"),
    "city": fields.String(description="Filter by city (optional)"),
    "limit": fields.Integer(default=100, description="Maximum results to return")
})

@properties_ns.route('/search/value-range')
class PropertyValueRangeSearch(Resource):
    """Search properties by value range"""
    
    @properties_ns.doc("search_by_value_range")
    @properties_ns.expect(value_range_model)
    def post(self):
        """Search properties by value range"""
        data = request.json
        min_value = data.get('min_value', 0)
        max_value = data.get('max_value', 10000000)
        city = data.get('city')
        limit = data.get('limit', 100)

        hcad_client = PostgresHCADClient()
        properties = hcad_client.search_by_value_range(
            min_value, max_value, city, limit
        )

        # Calculate statistics
        if properties:
            avg_value = sum(p['market_value'] for p in properties) / len(properties)
            avg_sqft = sum(p['building_sqft'] for p in properties if p['building_sqft'] > 0) / max(1, len([p for p in properties if p['building_sqft'] > 0]))
        else:
            avg_value = 0
            avg_sqft = 0

        return {
            "search_criteria": {
                "min_value": min_value,
                "max_value": max_value,
                "city": city,
                "limit": limit
            },
            "count": len(properties),
            "statistics": {
                "average_value": avg_value,
                "average_sqft": avg_sqft,
                "total_properties_value": sum(p['market_value'] for p in properties)
            },
            "properties": properties
        }


@properties_ns.route('/neighborhoods/<string:city>/stats')
class NeighborhoodStats(Resource):
    """Get neighborhood statistics"""
    
    @properties_ns.doc("get_neighborhood_stats")
    def get(self, city):
        """Get neighborhood statistics"""
        hcad_client = PostgresHCADClient()
        perplexity_client = PerplexityClient()
        
        stats = hcad_client.get_neighborhood_stats(city)

        # Enhance with Perplexity insights
        market_insights = None
        try:
            perplexity_data = perplexity_client.query(
                f"{city} Houston real estate market trends analysis investment opportunities"
            )
            if perplexity_data.get('success'):
                market_insights = perplexity_data.get('data')
        except:
            pass

        return {
            "city": city,
            "statistics": stats,
            "market_insights": market_insights,
            "data_source": "PostgreSQL Database",
            "timestamp": datetime.now().isoformat()
        }


# Location-based search model
location_search_model = properties_ns.model("LocationSearch", {
    "latitude": fields.Float(required=True, description="Latitude"),
    "longitude": fields.Float(required=True, description="Longitude"),
    "radius_miles": fields.Float(default=0.5, description="Search radius in miles"),
    "limit": fields.Integer(default=20, description="Maximum results")
})

@properties_ns.route('/search/near-location')
class PropertyLocationSearch(Resource):
    """Search properties near a location"""
    
    @properties_ns.doc("search_near_location")
    @properties_ns.expect(location_search_model)
    def post(self):
        """Find properties within radius of coordinates"""
        data = request.json
        lat = data.get('latitude')
        lon = data.get('longitude')
        radius = data.get('radius_miles', 0.5)
        limit = data.get('limit', 20)
        
        if not lat or not lon:
            raise ValidationError("Latitude and longitude are required")
        
        hcad_client = PostgresHCADClient()
        properties = hcad_client.get_properties_near_location(
            lat, lon, radius, limit
        )
        
        return {
            "search_location": {
                "latitude": lat,
                "longitude": lon,
                "radius_miles": radius
            },
            "count": len(properties),
            "properties": properties
        }


@properties_ns.route('/location')
class PropertyLocationGet(Resource):
    """Get properties near location via GET request"""
    
    @properties_ns.doc("get_properties_near_location",
        params={
            'lat': 'Latitude coordinate',
            'lon': 'Longitude coordinate', 
            'radius_miles': 'Search radius in miles (default: 1)',
            'limit': 'Maximum results (default: 20)'
        })
    def get(self):
        """Find properties within radius of coordinates"""
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius = request.args.get('radius_miles', 1.0, type=float)
        limit = min(request.args.get('limit', 100, type=int), 500)  # Default 100, max 500
        
        if not lat or not lon:
            raise ValidationError("lat and lon query parameters are required")
        
        hcad_client = PostgresHCADClient()
        properties = hcad_client.get_properties_near_location(
            lat, lon, radius, limit
        )
        
        return {
            "search_location": {
                "latitude": lat,
                "longitude": lon,
                "radius_miles": radius
            },
            "count": len(properties),
            "properties": properties
        }


@properties_ns.route('/all')
class AllProperties(Resource):
    """Browse all properties with pagination"""
    
    @properties_ns.doc("get_all_properties",
        params={
            'page': 'Page number (default: 1)',
            'per_page': 'Results per page (default: 100, max: 1000)',
            'city': 'Filter by city (optional)',
            'min_value': 'Minimum property value (optional)',
            'max_value': 'Maximum property value (optional)'
        })
    def get(self):
        """Get paginated list of all properties"""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 100, type=int), 1000)
        city = request.args.get('city', type=str)
        min_value = request.args.get('min_value', type=float)
        max_value = request.args.get('max_value', type=float)
        
        offset = (page - 1) * per_page
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        db_url = os.getenv('DATABASE_URL')
        
        try:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Build query with filters
                    query = "SELECT * FROM properties WHERE 1=1"
                    params = []
                    
                    if city:
                        query += " AND city = %s"
                        params.append(city.upper())
                    
                    if min_value is not None:
                        query += " AND total_value >= %s"
                        params.append(min_value)
                        
                    if max_value is not None:
                        query += " AND total_value <= %s"
                        params.append(max_value)
                    
                    # Get total count
                    count_query = f"SELECT COUNT(*) as total FROM ({query}) as filtered"
                    cur.execute(count_query, params)
                    total_count = cur.fetchone()['total']
                    
                    # Get paginated results
                    query += " ORDER BY account_number LIMIT %s OFFSET %s"
                    params.extend([per_page, offset])
                    
                    cur.execute(query, params)
                    properties = [dict(row) for row in cur.fetchall()]
                    
                    # Format response
                    return {
                        "page": page,
                        "per_page": per_page,
                        "total": total_count,
                        "total_pages": (total_count + per_page - 1) // per_page,
                        "count": len(properties),
                        "properties": properties,
                        "has_next": page * per_page < total_count,
                        "has_prev": page > 1
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching properties: {str(e)}")
            raise ValidationError(f"Database error: {str(e)}")


@properties_ns.route('/<string:account_number>/similar')
class SimilarProperties(Resource):
    """Find similar properties to a given property"""
    
    @properties_ns.doc("find_similar_properties")
    def get(self, account_number):
        """Find properties similar to this one within 1 mile radius"""
        hcad_client = PostgresHCADClient()
        
        # First get the target property
        property_data = hcad_client.search_by_account(account_number)
        
        if not property_data:
            return {
                "error": "Property not found",
                "account_number": account_number
            }, 404
        
        # Get radius and limit from query params
        radius = request.args.get('radius', 1.0, type=float)
        limit = request.args.get('limit', 20, type=int)
        
        # Find similar properties
        similar = hcad_client.find_similar_properties(
            property_data, 
            radius_miles=radius,
            limit=limit
        )
        
        return {
            "target_property": {
                "account_number": account_number,
                "address": property_data.get('property_address'),
                "value": property_data.get('market_value', 0),
                "type": property_data.get('property_type')
            },
            "search_radius_miles": radius,
            "similar_properties_count": len(similar),
            "similar_properties": similar
        }