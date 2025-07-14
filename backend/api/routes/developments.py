"""Development data endpoints"""

from flask_restx import Namespace, Resource

developments_ns = Namespace("developments", description="Development data operations")

@developments_ns.route("/active")
class ActiveDevelopments(Resource):
    """Active developments endpoint"""
    
    @developments_ns.doc("get_active_developments")
    def get(self):
        """Get active developments"""
        return {"message": "Active developments - Coming soon"}