"""Natural language query endpoint"""

from flask import request
from flask_restx import Namespace, Resource, fields

from backend.services.perplexity_client import PerplexityClient
from backend.utils.exceptions import ValidationError

query_ns = Namespace("query", description="Natural language query operations")

# Request/Response models
query_request_model = query_ns.model("QueryRequest", {
    "query": fields.String(required=True, description="Natural language query"),
    "context": fields.Raw(description="Additional context for the query")
})

query_response_model = query_ns.model("QueryResponse", {
    "data": fields.Raw(description="Query response data", required=True),
    "metadata": fields.Raw(description="Response metadata", required=True),
    "success": fields.Boolean(description="Success status", required=True)
})

@query_ns.route("")
class NaturalLanguageQuery(Resource):
    """Natural language query endpoint"""
    
    @query_ns.doc("natural_language_query")
    @query_ns.expect(query_request_model)
    @query_ns.marshal_with(query_response_model)
    def post(self):
        """Process a natural language query about Houston real estate"""
        data = request.get_json()
        
        if not data or "query" not in data:
            raise ValidationError("Query field is required")
        
        query = data["query"]
        context = data.get("context", {})
        
        # Initialize Perplexity client
        client = PerplexityClient()
        
        # Enhance query with Houston context
        enhanced_query = f"Houston, TX real estate: {query}"
        
        # Execute query
        response = client.query(enhanced_query)
        
        return response