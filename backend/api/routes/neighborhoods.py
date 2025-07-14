"""Neighborhood data endpoints"""

from flask_restx import Namespace, Resource

neighborhoods_ns = Namespace("neighborhoods", description="Neighborhood data operations")

@neighborhoods_ns.route("/<string:name>")
class NeighborhoodDetail(Resource):
    """Neighborhood detail endpoint"""
    
    @neighborhoods_ns.doc("get_neighborhood")
    def get(self, name):
        """Get neighborhood details"""
        return {"message": f"Neighborhood {name} details - Coming soon"}