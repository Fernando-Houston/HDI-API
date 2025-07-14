"""Search and autocomplete endpoints"""

from flask import request
from flask_restx import Namespace, Resource, fields
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict
import time

from backend.config.settings import settings
from backend.utils.exceptions import ValidationError

search_ns = Namespace("search", description="Search and autocomplete operations")

# Models
autocomplete_model = search_ns.model("AutocompleteRequest", {
    "query": fields.String(required=True, min_length=3, description="Search query (min 3 chars)"),
    "limit": fields.Integer(default=10, description="Maximum results to return"),
    "include_partial": fields.Boolean(default=True, description="Include partial matches from middle of address")
})

search_result_model = search_ns.model("SearchResult", {
    "address": fields.String,
    "account_number": fields.String,
    "owner_name": fields.String,
    "property_type": fields.String,
    "match_type": fields.String(enum=["exact", "starts_with", "contains"]),
    "relevance_score": fields.Float
})

@search_ns.route("/autocomplete")
class PropertyAutocomplete(Resource):
    """Autocomplete for property addresses"""
    
    @search_ns.doc("autocomplete_addresses")
    @search_ns.expect(autocomplete_model)
    def post(self):
        """Get autocomplete suggestions for property addresses"""
        data = request.get_json()
        query = data.get("query", "").strip().upper()
        limit = min(data.get("limit", 10), 50)  # Cap at 50
        include_partial = data.get("include_partial", True)
        
        # Validate minimum length
        if len(query) < 3:
            raise ValidationError("Query must be at least 3 characters")
        
        start_time = time.time()
        
        try:
            # Get database URL from environment
            db_url = os.getenv('DATABASE_URL')
            
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    results = []
                    
                    # First, try exact prefix match
                    cur.execute("""
                        SELECT DISTINCT 
                            property_address,
                            account_number,
                            owner_name,
                            property_type
                        FROM properties
                        WHERE UPPER(property_address) LIKE %s
                        ORDER BY property_address
                        LIMIT %s
                    """, (f'{query}%', limit))
                    
                    exact_matches = cur.fetchall()
                    for row in exact_matches:
                        results.append({
                            **dict(row),
                            'match_type': 'starts_with',
                            'relevance_score': 1.0
                        })
                    
                    # If we need more results and partial matching is enabled
                    if len(results) < limit and include_partial:
                        remaining = limit - len(results)
                        
                        # Search for partial matches (contains)
                        cur.execute("""
                            SELECT DISTINCT 
                                property_address,
                                account_number,
                                owner_name,
                                property_type
                            FROM properties
                            WHERE UPPER(property_address) LIKE %s
                            AND UPPER(property_address) NOT LIKE %s
                            ORDER BY 
                                LENGTH(property_address),
                                property_address
                            LIMIT %s
                        """, (f'%{query}%', f'{query}%', remaining))
                        
                        partial_matches = cur.fetchall()
                        for row in partial_matches:
                            # Calculate relevance based on position
                            address = row['property_address'].upper()
                            position = address.find(query)
                            relevance = 0.8 - (position / len(address) * 0.3)
                            
                            results.append({
                                **dict(row),
                                'match_type': 'contains',
                                'relevance_score': relevance
                            })
            
            # Sort by relevance
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "query": data.get("query"),
                "count": len(results),
                "results": results,
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"Autocomplete error: {str(e)}")
            raise ValidationError(f"Search error: {str(e)}")


@search_ns.route("/fuzzy")
class FuzzyPropertySearch(Resource):
    """Fuzzy search for properties"""
    
    @search_ns.doc("fuzzy_search")
    def get(self):
        """Fuzzy search using trigram similarity"""
        query = request.args.get("q", "").strip()
        
        if len(query) < 3:
            raise ValidationError("Query must be at least 3 characters")
        
        try:
            db_url = os.getenv('DATABASE_URL')
            
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # First ensure pg_trgm extension exists
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    
                    # Fuzzy search using trigram similarity
                    cur.execute("""
                        SELECT 
                            property_address,
                            account_number,
                            owner_name,
                            property_type,
                            similarity(property_address, %s) AS similarity_score
                        FROM properties
                        WHERE property_address %% %s
                        ORDER BY similarity_score DESC
                        LIMIT 20
                    """, (query, query))
                    
                    results = []
                    for row in cur.fetchall():
                        results.append({
                            **dict(row),
                            'match_type': 'fuzzy',
                            'relevance_score': row['similarity_score']
                        })
                    
                    return {
                        "query": query,
                        "count": len(results),
                        "results": results
                    }
                    
        except Exception as e:
            logger.error(f"Fuzzy search error: {str(e)}")
            raise ValidationError(f"Search error: {str(e)}")


@search_ns.route("/owners")
class OwnerAutocomplete(Resource):
    """Autocomplete for property owners"""
    
    @search_ns.doc("autocomplete_owners")
    def get(self):
        """Get autocomplete suggestions for owner names"""
        query = request.args.get("q", "").strip().upper()
        
        if len(query) < 3:
            raise ValidationError("Query must be at least 3 characters")
        
        try:
            db_url = os.getenv('DATABASE_URL')
            
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT DISTINCT 
                            owner_name,
                            COUNT(*) as property_count,
                            SUM(total_value) as total_portfolio_value
                        FROM properties
                        WHERE UPPER(owner_name) LIKE %s
                        GROUP BY owner_name
                        ORDER BY property_count DESC
                        LIMIT 20
                    """, (f'%{query}%',))
                    
                    results = []
                    for row in cur.fetchall():
                        results.append({
                            'owner_name': row['owner_name'],
                            'property_count': row['property_count'],
                            'portfolio_value': float(row['total_portfolio_value'] or 0)
                        })
                    
                    return {
                        "query": request.args.get("q"),
                        "count": len(results),
                        "results": results
                    }
                    
        except Exception as e:
            logger.error(f"Owner search error: {str(e)}")
            raise ValidationError(f"Search error: {str(e)}")


# Add to routes registration
import os
import structlog
logger = structlog.get_logger(__name__)