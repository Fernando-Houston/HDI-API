"""API Routes Registration"""

from flask_restx import Api

def register_routes(api: Api) -> None:
    """Register all API routes"""
    
    # Import namespaces
    from backend.api.routes.market import market_ns
    from backend.api.routes.properties import properties_ns
    from backend.api.routes.neighborhoods import neighborhoods_ns
    from backend.api.routes.developments import developments_ns
    from backend.api.routes.query import query_ns
    from backend.api.routes.bulk import bulk_ns
    from backend.api.routes.analytics import analytics_ns
    from backend.api.routes.opportunities import opportunities_ns
    from backend.api.routes.permits import permits_ns
    from backend.api.routes.reports import reports_ns
    from backend.api.routes.batch import batch_ns
    from backend.api.routes.search import search_ns
    
    # Register namespaces
    api.add_namespace(market_ns, path="/market")
    api.add_namespace(properties_ns, path="/properties")
    api.add_namespace(neighborhoods_ns, path="/neighborhoods")
    api.add_namespace(developments_ns, path="/developments")
    api.add_namespace(query_ns, path="/query")
    api.add_namespace(bulk_ns, path="/bulk")
    api.add_namespace(analytics_ns, path="/analytics")
    api.add_namespace(opportunities_ns, path="/opportunities")
    api.add_namespace(permits_ns, path="/permits")
    api.add_namespace(reports_ns, path="/reports")
    api.add_namespace(batch_ns, path="/batch")
    api.add_namespace(search_ns, path="/search")