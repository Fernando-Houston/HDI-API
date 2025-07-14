"""Pre-optimized query templates for common Houston real estate queries"""

QUERY_TEMPLATES = {
    "market_overview": """
        Houston {area} real estate market analysis for {date}:
        
        Please provide current data including:
        - Current median home prices
        - Active inventory levels (number of homes for sale)
        - Average days on market
        - Price trends over the last 90 days
        - Year-over-year price comparison
        - Market temperature (buyer's market, seller's market, or balanced)
        - Key factors driving the market
        
        Format the response as structured data with specific numbers and cite sources.
    """,
    
    "investment_opportunities": """
        Investment opportunities in Houston {area} with budget {budget}:
        
        Analyze and provide:
        - Properties or areas with high ROI potential
        - Emerging neighborhoods showing growth
        - Below-market opportunities
        - Estimated rental yields
        - 5-year growth projections
        - Risk factors to consider
        - Comparable sales data
        
        Include specific examples and data sources.
    """,
    
    "neighborhood_analysis": """
        Comprehensive analysis of {neighborhood}, Houston, TX:
        
        Include:
        - Demographics (population, income, age distribution)
        - School ratings and districts
        - Crime statistics and safety rating
        - Walkability and transit scores
        - Local amenities and attractions
        - Recent development activity
        - Property tax rates
        - Flood risk assessment
        
        Provide current data with sources.
    """,
    
    "development_tracker": """
        Active real estate developments in Houston {area}:
        
        List:
        - Current construction projects (residential and commercial)
        - Planned developments with timelines
        - Recent building permit activity
        - Major developers involved
        - Expected completion dates
        - Impact on local property values
        - Infrastructure improvements planned
        
        Include project names, sizes, and sources.
    """,
    
    "property_research": """
        Property research for {address}, Houston, TX:
        
        Provide:
        - Last sale price and date
        - Current estimated value
        - Property tax history
        - Comparable sales in the area (last 6 months)
        - Neighborhood trends
        - School information
        - Flood zone status
        - Any liens or issues
        
        Use recent, verifiable data sources.
    """,
    
    "market_forecast": """
        Houston {area} real estate market forecast for {timeframe}:
        
        Analyze:
        - Expected price trends
        - Inventory projections
        - Economic factors affecting the market
        - Population growth impact
        - Major developments or infrastructure changes
        - Interest rate considerations
        - Investment recommendations
        
        Base projections on current trends and cite sources.
    """,
    
    "rental_analysis": """
        Rental market analysis for {area}, Houston:
        
        Include:
        - Current median rent prices by bedroom count
        - Vacancy rates
        - Rental yield percentages
        - Tenant demographics
        - Most in-demand features
        - Seasonal trends
        - Comparison to purchase prices
        - Growth trends year-over-year
        
        Provide specific numbers and sources.
    """,
    
    "flood_risk_assessment": """
        Flood risk assessment for {address_or_area}, Houston, TX:
        
        Detail:
        - FEMA flood zone designation
        - Historical flooding events
        - Elevation data
        - Drainage infrastructure
        - Insurance requirements and costs
        - Mitigation measures in place
        - Future risk projections
        
        Include official sources and recent data.
    """,
    
    "commercial_opportunities": """
        Commercial real estate opportunities in Houston {area}:
        
        Analyze:
        - Available properties (office, retail, industrial)
        - Lease rates and cap rates
        - Vacancy rates by property type
        - Major tenants and industries
        - Development pipeline
        - Investment potential
        - Market drivers
        
        Focus on current market conditions with data.
    """,
    
    "comparative_analysis": """
        Compare real estate markets: {area1} vs {area2} in Houston:
        
        Compare:
        - Median home prices
        - Price appreciation (1, 3, 5 year)
        - Days on market
        - Inventory levels
        - Demographics
        - School ratings
        - Crime rates
        - Future development plans
        - Investment potential
        
        Provide side-by-side comparison with sources.
    """
}

# Quick query templates for common questions
QUICK_QUERIES = {
    "median_price": "What is the current median home price in {area}, Houston, TX? Provide the most recent data available.",
    
    "inventory": "How many homes are currently for sale in {area}, Houston, TX? Include breakdown by price range if available.",
    
    "best_schools": "What are the top-rated schools in {area}, Houston, TX? Include ratings and test scores.",
    
    "crime_rate": "What is the current crime rate in {area}, Houston, TX? Compare to Houston average.",
    
    "new_construction": "What new construction projects are happening in {area}, Houston, TX?",
    
    "flood_zone": "Is {address} in a flood zone in Houston, TX? What is the FEMA designation?",
    
    "property_tax": "What is the property tax rate in {area}, Houston, TX? How does it compare to other Houston areas?",
    
    "appreciation": "What has been the home price appreciation rate in {area}, Houston, TX over the last 5 years?"
}