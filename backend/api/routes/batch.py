"""Batch operations for analyzing multiple properties at once"""

from flask import request
from flask_restx import Namespace, Resource, fields
import concurrent.futures
from typing import List, Dict
import time

from backend.services.data_fusion import DataFusionEngine
from backend.services.postgres_hcad_client import PostgresHCADClient
from backend.utils.exceptions import ValidationError

batch_ns = Namespace("batch", description="Batch property operations")

# Request/Response models
batch_request_model = batch_ns.model("BatchPropertyRequest", {
    "addresses": fields.List(fields.String, required=True, description="List of property addresses", max_items=100),
    "include_market_data": fields.Boolean(default=True, description="Include Perplexity market analysis"),
    "include_geometry": fields.Boolean(default=True, description="Include property geometry data"),
    "include_similar": fields.Boolean(default=False, description="Include similar properties for each")
})

property_summary_model = batch_ns.model("PropertySummary", {
    "address": fields.String,
    "account_number": fields.String,
    "owner_name": fields.String,
    "market_value": fields.Float,
    "property_type": fields.String,
    "geometry": fields.Raw,
    "status": fields.String(enum=["success", "not_found", "error"]),
    "error_message": fields.String
})

batch_response_model = batch_ns.model("BatchPropertyResponse", {
    "request_id": fields.String(description="Unique batch request ID"),
    "total_requested": fields.Integer,
    "successful": fields.Integer,
    "failed": fields.Integer,
    "processing_time_ms": fields.Float,
    "properties": fields.List(fields.Nested(property_summary_model)),
    "summary": fields.Raw(description="Aggregate statistics")
})

@batch_ns.route("/analyze")
class BatchPropertyAnalysis(Resource):
    """Batch property analysis endpoint"""
    
    @batch_ns.doc("batch_analyze_properties")
    @batch_ns.expect(batch_request_model)
    @batch_ns.marshal_with(batch_response_model)
    def post(self):
        """Analyze multiple properties in a single request"""
        start_time = time.time()
        data = request.get_json()
        
        # Validate input
        addresses = data.get("addresses", [])
        if not addresses:
            raise ValidationError("No addresses provided")
        
        if len(addresses) > 100:
            raise ValidationError("Maximum 100 properties per batch request")
        
        # Remove duplicates
        addresses = list(set(addresses))
        
        # Initialize clients
        hcad_client = PostgresHCADClient()
        fusion_engine = DataFusionEngine() if data.get("include_market_data") else None
        
        # Process properties in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            futures = {}
            for address in addresses:
                future = executor.submit(self._process_single_property, 
                                       address, hcad_client, fusion_engine, data)
                futures[future] = address
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                address = futures[future]
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    results.append({
                        "address": address,
                        "status": "error",
                        "error_message": str(e)
                    })
        
        # Calculate summary statistics
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") != "success"]
        
        summary = self._calculate_summary(successful)
        
        # Generate response
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "request_id": f"batch_{int(time.time())}",
            "total_requested": len(addresses),
            "successful": len(successful),
            "failed": len(failed),
            "processing_time_ms": processing_time,
            "properties": results,
            "summary": summary
        }
    
    def _process_single_property(self, address: str, hcad_client, fusion_engine, options: Dict) -> Dict:
        """Process a single property"""
        try:
            # Get basic property data
            property_data = hcad_client.get_property_data(address)
            
            if not property_data:
                return {
                    "address": address,
                    "status": "not_found",
                    "error_message": "Property not found in database"
                }
            
            # Build response
            result = {
                "address": property_data.get("property_address"),
                "account_number": property_data.get("account_number"),
                "owner_name": property_data.get("owner_name"),
                "market_value": property_data.get("market_value", 0),
                "property_type": property_data.get("property_type"),
                "status": "success"
            }
            
            # Add geometry if requested
            if options.get("include_geometry") and property_data.get("geometry"):
                result["geometry"] = property_data["geometry"]
            
            # Add market data if requested
            if fusion_engine and options.get("include_market_data"):
                # Note: This will use cached Perplexity responses when available
                intelligence = fusion_engine.get_property_intelligence(address)
                if intelligence.get("market_insights"):
                    result["has_market_insights"] = True
                    result["confidence_score"] = intelligence.get("confidence_score", 0)
            
            return result
            
        except Exception as e:
            return {
                "address": address,
                "status": "error",
                "error_message": str(e)
            }
    
    def _calculate_summary(self, properties: List[Dict]) -> Dict:
        """Calculate summary statistics for successful properties"""
        if not properties:
            return {}
        
        total_value = sum(p.get("market_value", 0) for p in properties)
        values = [p.get("market_value", 0) for p in properties if p.get("market_value", 0) > 0]
        
        return {
            "total_portfolio_value": total_value,
            "average_value": sum(values) / len(values) if values else 0,
            "min_value": min(values) if values else 0,
            "max_value": max(values) if values else 0,
            "properties_with_value": len(values),
            "properties_without_value": len(properties) - len(values),
            "property_types": self._count_types(properties),
            "unique_owners": len(set(p.get("owner_name", "") for p in properties))
        }
    
    def _count_types(self, properties: List[Dict]) -> Dict[str, int]:
        """Count properties by type"""
        type_counts = {}
        for prop in properties:
            prop_type = prop.get("property_type", "Unknown")
            type_counts[prop_type] = type_counts.get(prop_type, 0) + 1
        return type_counts


@batch_ns.route("/compare")
class BatchPropertyComparison(Resource):
    """Compare multiple properties side by side"""
    
    @batch_ns.doc("compare_properties")
    def post(self):
        """Compare up to 10 properties with detailed analysis"""
        data = request.get_json()
        addresses = data.get("addresses", [])
        
        if len(addresses) > 10:
            raise ValidationError("Maximum 10 properties for comparison")
        
        # Get all properties
        hcad_client = PostgresHCADClient()
        properties = []
        
        for address in addresses:
            prop_data = hcad_client.get_property_data(address)
            if prop_data:
                properties.append(prop_data)
        
        if not properties:
            return {"error": "No valid properties found"}, 404
        
        # Create comparison matrix
        comparison = {
            "properties": properties,
            "metrics": {
                "value_range": {
                    "min": min(p.get("market_value", 0) for p in properties),
                    "max": max(p.get("market_value", 0) for p in properties)
                },
                "building_size_range": {
                    "min": min(p.get("building_sqft", 0) for p in properties),
                    "max": max(p.get("building_sqft", 0) for p in properties)
                },
                "year_built_range": {
                    "oldest": min(p.get("year_built", 9999) for p in properties),
                    "newest": max(p.get("year_built", 0) for p in properties)
                }
            },
            "recommendations": self._generate_comparison_insights(properties)
        }
        
        return comparison
    
    def _generate_comparison_insights(self, properties: List[Dict]) -> List[str]:
        """Generate insights from property comparison"""
        insights = []
        
        # Value insights
        values = [p.get("market_value", 0) for p in properties if p.get("market_value", 0) > 0]
        if values:
            avg_value = sum(values) / len(values)
            if max(values) > avg_value * 1.5:
                insights.append(f"Significant value disparity - highest is {max(values)/avg_value:.1f}x average")
        
        # Age insights
        years = [p.get("year_built", 0) for p in properties if p.get("year_built", 0) > 0]
        if years and max(years) - min(years) > 20:
            insights.append(f"Properties span {max(years) - min(years)} years in age")
        
        return insights