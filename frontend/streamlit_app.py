"""HDI Streamlit Dashboard - Houston Data Intelligence Platform"""

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import time

# Page configuration
st.set_page_config(
    page_title="HDI - Houston Data Intelligence",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_BASE_URL = "http://localhost:5000/api/v1"
HOUSTON_NEIGHBORHOODS = [
    "Houston Heights", "Montrose", "River Oaks", "Memorial", "Tanglewood",
    "Downtown", "Midtown", "EaDo", "Third Ward", "East End", "Acres Homes",
    "Sunnyside", "Galleria", "Uptown", "Washington Ave", "The Woodlands"
]

class HDIClient:
    """Client for HDI API"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/../health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def search_properties(self, query: str) -> Dict[str, Any]:
        """Natural language property search"""
        try:
            response = self.session.post(
                f"{self.base_url}/query",
                json={"query": query},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_property(self, address: str) -> Dict[str, Any]:
        """Analyze specific property"""
        try:
            response = self.session.get(
                f"{self.base_url}/properties/analyze",
                params={"address": address},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_market_trends(self, area: str) -> Dict[str, Any]:
        """Get market trends for area"""
        try:
            response = self.session.get(
                f"{self.base_url}/market/trends",
                params={"area": area},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_opportunities(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Find investment opportunities"""
        try:
            response = self.session.post(
                f"{self.base_url}/opportunities/find",
                json=criteria,
                timeout=45
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"opportunities": [], "error": str(e)}
    
    def get_permits(self, address: str = None, area: str = None) -> List[Dict[str, Any]]:
        """Get building permits"""
        try:
            if address:
                response = self.session.get(
                    f"{self.base_url}/permits/by-address",
                    params={"address": address, "days_back": 365},
                    timeout=20
                )
            elif area:
                response = self.session.get(
                    f"{self.base_url}/permits/by-area",
                    params={"neighborhood": area, "days_back": 90},
                    timeout=20
                )
            else:
                return []
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []
    
    def generate_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate automated report"""
        try:
            response = self.session.post(
                f"{self.base_url}/reports/generate",
                json=config,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get platform analytics"""
        try:
            response = self.session.get(
                f"{self.base_url}/analytics/stats/daily",
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {}

# Initialize client
@st.cache_resource
def get_hdi_client():
    return HDIClient()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .opportunity-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
    }
    .stButton > button {
        background-color: #1f4e79;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
    }
    .sidebar .sidebar-content {
        background: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

def render_header():
    """Render main header"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown('<h1 class="main-header">🏠 HDI Dashboard</h1>', unsafe_allow_html=True)
        st.caption("Houston Data Intelligence Platform")
    
    with col2:
        # API Health Check
        client = get_hdi_client()
        if client.health_check():
            st.success("API Online")
        else:
            st.error("API Offline")
    
    with col3:
        st.metric("Platform", "v2.0", "Phase 2")

def render_sidebar():
    """Render sidebar navigation"""
    st.sidebar.title("🔍 Navigation")
    
    pages = {
        "🏠 Property Search": "search",
        "📊 Market Analysis": "market", 
        "💰 Opportunities": "opportunities",
        "🏗️ Permits": "permits",
        "📋 Reports": "reports",
        "📈 Analytics": "analytics"
    }
    
    selected = st.sidebar.radio("Select Page", list(pages.keys()))
    return pages[selected]

def render_property_search():
    """Property search page"""
    st.header("🔍 Property Search & Analysis")
    
    # Search methods
    search_type = st.selectbox(
        "Search Method",
        ["Natural Language Search", "Address Analysis", "Bulk Compare"]
    )
    
    client = get_hdi_client()
    
    if search_type == "Natural Language Search":
        st.subheader("Ask anything about Houston real estate")
        
        query = st.text_input(
            "Your Question",
            placeholder="e.g., 3 bedroom houses under $400k in Heights with good investment potential"
        )
        
        if st.button("Search", key="search_btn") and query:
            with st.spinner("Searching..."):
                result = client.search_properties(query)
            
            if result.get("success"):
                st.success("Search completed!")
                st.markdown("### Results")
                st.write(result.get("data", "No results found"))
                
                # Show metadata
                if result.get("metadata"):
                    with st.expander("Query Details"):
                        meta = result["metadata"]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Response Time", f"{meta.get('response_time', 0):.2f}s")
                        with col2:
                            st.metric("Cost", f"${meta.get('cost', 0):.4f}")
                        with col3:
                            st.metric("Cache Hit", "Yes" if meta.get('from_cache') else "No")
            else:
                st.error(f"Search failed: {result.get('error', 'Unknown error')}")
    
    elif search_type == "Address Analysis":
        st.subheader("Analyze a specific property")
        
        address = st.text_input(
            "Property Address",
            placeholder="e.g., 1234 Main St, Houston, TX"
        )
        
        if st.button("Analyze Property", key="analyze_btn") and address:
            with st.spinner("Analyzing property..."):
                result = client.analyze_property(address)
            
            if not result.get("error"):
                render_property_analysis(result)
            else:
                st.error(f"Analysis failed: {result['error']}")
    
    elif search_type == "Bulk Compare":
        st.subheader("Compare multiple properties")
        
        addresses = st.text_area(
            "Property Addresses (one per line)",
            placeholder="1000 Main St, Houston, TX\n2000 Bagby St, Houston, TX\n3000 Post Oak, Houston, TX"
        )
        
        if st.button("Compare Properties", key="compare_btn") and addresses:
            address_list = [addr.strip() for addr in addresses.split('\n') if addr.strip()]
            
            if len(address_list) > 5:
                st.warning("Maximum 5 properties allowed for comparison")
                address_list = address_list[:5]
            
            st.info(f"Comparing {len(address_list)} properties...")
            # Implementation would call bulk compare API

def render_property_analysis(data: Dict[str, Any]):
    """Render property analysis results"""
    st.success("Property analysis complete!")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    official_data = data.get("official_data", {})
    
    with col1:
        if "appraised_value" in official_data:
            st.metric("Appraised Value", official_data["appraised_value"])
    
    with col2:
        if "year_built" in official_data:
            st.metric("Year Built", official_data["year_built"])
    
    with col3:
        if "living_area" in official_data:
            st.metric("Living Area", official_data["living_area"])
    
    with col4:
        confidence = data.get("confidence_score", 0)
        st.metric("Confidence", f"{confidence:.1%}")
    
    # Market insights
    if data.get("market_insights"):
        st.subheader("📈 Market Insights")
        st.write(data["market_insights"])
    
    # Recommendations
    if data.get("recommendations"):
        st.subheader("💡 Recommendations")
        for rec in data["recommendations"]:
            st.write(f"• {rec}")
    
    # Permit insights
    if data.get("permit_insights"):
        st.subheader("🏗️ Permit Activity")
        permit_data = data["permit_insights"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Status:** {permit_data.get('renovation_status', 'Unknown')}")
            st.write(f"**Investment Level:** ${permit_data.get('investment_level', 0):,.0f}")
        
        with col2:
            if permit_data.get("property_improvements"):
                st.write("**Recent Improvements:**")
                for improvement in permit_data["property_improvements"]:
                    st.write(f"• {improvement}")

def render_market_analysis():
    """Market analysis page"""
    st.header("📊 Market Analysis")
    
    # Area selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_area = st.selectbox(
            "Select Houston Area",
            HOUSTON_NEIGHBORHOODS,
            index=0
        )
    
    with col2:
        if st.button("Analyze Market", key="market_btn"):
            client = get_hdi_client()
            
            with st.spinner(f"Analyzing {selected_area} market..."):
                result = client.get_market_trends(selected_area)
            
            if result.get("success"):
                st.subheader(f"📈 {selected_area} Market Trends")
                st.write(result.get("data", "No market data available"))
                
                # Get permits for the area
                permits = client.get_permits(area=selected_area)
                if permits:
                    render_permits_chart(permits, selected_area)
            else:
                st.error(f"Market analysis failed: {result.get('error', 'Unknown error')}")

def render_opportunities():
    """Investment opportunities page"""
    st.header("💰 Investment Opportunities")
    
    # Search criteria
    with st.expander("🎯 Search Criteria", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            neighborhoods = st.multiselect(
                "Neighborhoods",
                HOUSTON_NEIGHBORHOODS,
                default=["Houston Heights", "Montrose"]
            )
            
            max_price = st.number_input(
                "Max Price ($)",
                min_value=50000,
                max_value=2000000,
                value=500000,
                step=25000
            )
        
        with col2:
            property_types = st.multiselect(
                "Property Types",
                ["single-family", "multi-family", "condo", "townhouse"],
                default=["single-family", "multi-family"]
            )
            
            min_cap_rate = st.slider(
                "Min Cap Rate (%)",
                min_value=3.0,
                max_value=15.0,
                value=6.0,
                step=0.5
            )
        
        with col3:
            distressed = st.checkbox("Include Distressed Properties", True)
            renovated = st.checkbox("Recently Renovated Only", False)
    
    if st.button("Find Opportunities", key="opp_btn"):
        criteria = {
            "neighborhoods": neighborhoods,
            "max_price": max_price,
            "property_types": property_types,
            "min_cap_rate": min_cap_rate,
            "distressed": distressed,
            "recently_renovated": renovated
        }
        
        client = get_hdi_client()
        
        with st.spinner("Finding investment opportunities..."):
            result = client.find_opportunities(criteria)
        
        if result.get("opportunities"):
            render_opportunities_results(result["opportunities"])
        else:
            if result.get("error"):
                st.error(f"Search failed: {result['error']}")
            else:
                st.info("No opportunities found matching your criteria")

def render_opportunities_results(opportunities: List[Dict[str, Any]]):
    """Render opportunities search results"""
    st.success(f"Found {len(opportunities)} investment opportunities!")
    
    for i, opp in enumerate(opportunities, 1):
        with st.container():
            st.markdown(f"""
            <div class="opportunity-card">
                <h4>#{i}. {opp.get('address', 'Unknown Address')}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if 'estimated_price' in opp:
                    st.metric("Est. Price", f"${opp['estimated_price']:,.0f}")
            
            with col2:
                if 'match_score' in opp:
                    st.metric("Match Score", f"{opp['match_score']:.1f}/10")
            
            with col3:
                if 'estimated_roi' in opp:
                    st.metric("Est. ROI", f"{opp['estimated_roi']:.1%}")
            
            with col4:
                if 'cap_rate' in opp:
                    st.metric("Cap Rate", f"{opp['cap_rate']:.1%}")
            
            # Match reasons
            if opp.get('match_reasons'):
                st.write("**Why this is a good match:**")
                for reason in opp['match_reasons'][:3]:
                    st.write(f"• {reason}")
            
            st.divider()

def render_permits():
    """Permits analysis page"""
    st.header("🏗️ Building Permits Analysis")
    
    search_type = st.radio(
        "Search Type",
        ["By Address", "By Neighborhood"]
    )
    
    client = get_hdi_client()
    
    if search_type == "By Address":
        address = st.text_input("Property Address")
        if st.button("Get Permits", key="permits_addr_btn") and address:
            permits = client.get_permits(address=address)
            if permits:
                render_permits_table(permits)
            else:
                st.info("No permits found for this address")
    
    else:
        neighborhood = st.selectbox("Select Neighborhood", HOUSTON_NEIGHBORHOODS)
        if st.button("Get Area Permits", key="permits_area_btn"):
            permits = client.get_permits(area=neighborhood)
            if permits:
                render_permits_table(permits)
                render_permits_chart(permits, neighborhood)
            else:
                st.info(f"No recent permits found in {neighborhood}")

def render_permits_table(permits: List[Dict[str, Any]]):
    """Render permits as a table"""
    if not permits:
        return
    
    df = pd.DataFrame(permits)
    
    # Select relevant columns
    display_columns = ['address', 'permit_type', 'description', 'estimated_cost', 'issue_date', 'status']
    available_columns = [col for col in display_columns if col in df.columns]
    
    if available_columns:
        st.dataframe(
            df[available_columns].head(20),
            use_container_width=True
        )

def render_permits_chart(permits: List[Dict[str, Any]], area: str):
    """Render permits visualization"""
    if not permits:
        return
    
    st.subheader(f"📊 Permit Activity in {area}")
    
    df = pd.DataFrame(permits)
    
    if 'estimated_cost' in df.columns and 'permit_type' in df.columns:
        # Group by permit type
        type_summary = df.groupby('permit_type')['estimated_cost'].agg(['count', 'sum']).reset_index()
        type_summary.columns = ['permit_type', 'count', 'total_value']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Permit count by type
            fig1 = px.bar(
                type_summary.head(10),
                x='permit_type',
                y='count',
                title='Permit Count by Type',
                labels={'count': 'Number of Permits', 'permit_type': 'Permit Type'}
            )
            fig1.update_xaxis(tickangle=45)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Total value by type
            fig2 = px.pie(
                type_summary.head(8),
                values='total_value',
                names='permit_type',
                title='Total Investment by Permit Type'
            )
            st.plotly_chart(fig2, use_container_width=True)

def render_reports():
    """Reports generation page"""
    st.header("📋 Automated Reports")
    
    # Report configuration
    col1, col2 = st.columns([2, 1])
    
    with col1:
        report_type = st.selectbox(
            "Report Type",
            [
                "daily_market",
                "weekly_summary", 
                "neighborhood_focus",
                "investment_opportunities",
                "permit_activity"
            ]
        )
        
        areas = st.multiselect(
            "Areas to Include",
            HOUSTON_NEIGHBORHOODS,
            default=["Houston Heights", "Montrose"]
        )
    
    with col2:
        include_permits = st.checkbox("Include Permits", True)
        include_opportunities = st.checkbox("Include Opportunities", True)
        include_analytics = st.checkbox("Include Analytics", False)
        
        max_opportunities = st.slider("Max Opportunities", 5, 20, 10)
    
    if st.button("Generate Report", key="gen_report_btn") and areas:
        config = {
            "report_type": report_type,
            "areas": areas,
            "include_permits": include_permits,
            "include_opportunities": include_opportunities,
            "include_analytics": include_analytics,
            "max_opportunities": max_opportunities
        }
        
        client = get_hdi_client()
        
        with st.spinner("Generating report..."):
            result = client.generate_report(config)
        
        if not result.get("error"):
            render_report_results(result)
        else:
            st.error(f"Report generation failed: {result['error']}")

def render_report_results(report: Dict[str, Any]):
    """Render generated report"""
    st.success("Report generated successfully!")
    
    # Report header
    st.subheader(report.get("title", "HDI Report"))
    st.caption(f"Generated: {report.get('generated_at', 'Unknown')}")
    
    # Report sections
    sections = report.get("sections", {})
    
    for section_name, section_data in sections.items():
        with st.expander(f"📊 {section_name.replace('_', ' ').title()}", expanded=True):
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if isinstance(value, (str, int, float)):
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    elif isinstance(value, list) and value:
                        st.write(f"**{key.replace('_', ' ').title()}:**")
                        for item in value[:5]:  # Show first 5 items
                            st.write(f"• {item}")
            else:
                st.write(section_data)
    
    # Download options
    st.markdown("### Download Report")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Download JSON"):
            st.download_button(
                label="Download JSON",
                data=json.dumps(report, indent=2),
                file_name=f"hdi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        # Note: Markdown/HTML download would require additional API calls
        st.info("Markdown/HTML formats available via API")

def render_analytics():
    """Platform analytics page"""
    st.header("📈 Platform Analytics")
    
    client = get_hdi_client()
    analytics = client.get_analytics()
    
    if analytics:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Queries Today",
                analytics.get("total_queries", 0)
            )
        
        with col2:
            st.metric(
                "Cache Hit Rate",
                f"{analytics.get('cache_hit_rate', 0):.1%}"
            )
        
        with col3:
            st.metric(
                "Total Cost",
                f"${analytics.get('total_cost', 0):.2f}"
            )
        
        with col4:
            st.metric(
                "Avg Response Time",
                f"{analytics.get('average_response_time', 0):.2f}s"
            )
        
        # Cost breakdown chart (placeholder)
        st.subheader("💰 Cost Breakdown")
        cost_data = {
            "Query Type": ["Market Analysis", "Property Search", "Opportunities", "Reports"],
            "Cost": [0.012, 0.008, 0.015, 0.004]  # Example data
        }
        
        fig = px.bar(
            cost_data,
            x="Query Type",
            y="Cost",
            title="Average Cost per Query Type"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.warning("Unable to load analytics data")

def main():
    """Main application"""
    render_header()
    
    # Sidebar navigation
    current_page = render_sidebar()
    
    # Page routing
    if current_page == "search":
        render_property_search()
    elif current_page == "market":
        render_market_analysis()
    elif current_page == "opportunities":
        render_opportunities()
    elif current_page == "permits":
        render_permits()
    elif current_page == "reports":
        render_reports()
    elif current_page == "analytics":
        render_analytics()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**HDI v2.0** - Houston Data Intelligence")
    st.sidebar.caption("Internal Team Platform")

if __name__ == "__main__":
    main()