"""Automated report generation service"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import structlog
from dataclasses import dataclass
from enum import Enum

from backend.services.perplexity_client import PerplexityClient
from backend.services.smart_search import SmartSearchEngine
from backend.services.permits_client import PermitsClient
from backend.monitoring.usage_tracker import usage_tracker
from backend.utils.exceptions import HDIException

logger = structlog.get_logger(__name__)

class ReportType(Enum):
    """Types of reports available"""
    DAILY_MARKET = "daily_market"
    WEEKLY_SUMMARY = "weekly_summary"
    NEIGHBORHOOD_FOCUS = "neighborhood_focus"
    INVESTMENT_OPPORTUNITIES = "investment_opportunities"
    PERMIT_ACTIVITY = "permit_activity"
    CUSTOM = "custom"

@dataclass
class ReportConfig:
    """Configuration for a report"""
    report_type: ReportType
    areas: List[str]  # Neighborhoods or ZIP codes
    include_permits: bool = True
    include_opportunities: bool = True
    include_analytics: bool = True
    custom_sections: Optional[List[str]] = None
    max_opportunities: int = 10

class ReportGenerator:
    """Generates automated market reports"""
    
    def __init__(self):
        self.perplexity = PerplexityClient()
        self.search_engine = SmartSearchEngine()
        self.permits = PermitsClient()
        logger.info("ReportGenerator initialized")
    
    def generate_report(
        self,
        config: ReportConfig,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate a report based on configuration
        
        Args:
            config: Report configuration
            format: Output format (json, html, markdown)
            
        Returns:
            Generated report
        """
        start_time = datetime.utcnow()
        logger.info(f"Generating {config.report_type.value} report", areas=config.areas)
        
        # Initialize report structure
        report = {
            "title": self._get_report_title(config),
            "generated_at": datetime.utcnow().isoformat(),
            "type": config.report_type.value,
            "areas": config.areas,
            "sections": {},
            "metadata": {
                "generation_time": 0,
                "data_sources": []
            }
        }
        
        try:
            # Generate report sections based on type
            if config.report_type == ReportType.DAILY_MARKET:
                report["sections"] = self._generate_daily_market_report(config)
            elif config.report_type == ReportType.WEEKLY_SUMMARY:
                report["sections"] = self._generate_weekly_summary(config)
            elif config.report_type == ReportType.NEIGHBORHOOD_FOCUS:
                report["sections"] = self._generate_neighborhood_report(config)
            elif config.report_type == ReportType.INVESTMENT_OPPORTUNITIES:
                report["sections"] = self._generate_investment_report(config)
            elif config.report_type == ReportType.PERMIT_ACTIVITY:
                report["sections"] = self._generate_permit_report(config)
            elif config.report_type == ReportType.CUSTOM:
                report["sections"] = self._generate_custom_report(config)
            
            # Add generation metadata
            report["metadata"]["generation_time"] = (datetime.utcnow() - start_time).total_seconds()
            report["metadata"]["success"] = True
            
            # Format output if requested
            if format == "markdown":
                return self._format_as_markdown(report)
            elif format == "html":
                return self._format_as_html(report)
            
            logger.info(
                "Report generated successfully",
                type=config.report_type.value,
                sections=len(report["sections"]),
                time=report["metadata"]["generation_time"]
            )
            
            return report
            
        except Exception as e:
            logger.error("Report generation failed", error=str(e))
            report["metadata"]["success"] = False
            report["metadata"]["error"] = str(e)
            return report
    
    def _generate_daily_market_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate daily market summary report"""
        sections = {}
        
        # 1. Market Overview
        market_overview = self._get_market_overview(config.areas)
        if market_overview:
            sections["market_overview"] = market_overview
        
        # 2. Today's Opportunities
        if config.include_opportunities:
            opportunities = self._get_todays_opportunities(config.areas, config.max_opportunities)
            if opportunities:
                sections["opportunities"] = opportunities
        
        # 3. Permit Activity
        if config.include_permits:
            permit_activity = self._get_recent_permit_activity(config.areas)
            if permit_activity:
                sections["permit_activity"] = permit_activity
        
        # 4. Market Pulse
        market_pulse = self._get_market_pulse(config.areas)
        if market_pulse:
            sections["market_pulse"] = market_pulse
        
        # 5. Usage Analytics (internal)
        if config.include_analytics:
            analytics = self._get_usage_analytics()
            if analytics:
                sections["platform_analytics"] = analytics
        
        return sections
    
    def _generate_weekly_summary(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate weekly summary report"""
        sections = {}
        
        # 1. Week in Review
        week_review = self._get_week_in_review(config.areas)
        sections["week_in_review"] = week_review
        
        # 2. Top Opportunities This Week
        if config.include_opportunities:
            opportunities = self._get_weekly_opportunities(config.areas)
            sections["top_opportunities"] = opportunities
        
        # 3. Neighborhood Trends
        trends = self._get_neighborhood_trends(config.areas)
        sections["neighborhood_trends"] = trends
        
        # 4. Development Activity
        if config.include_permits:
            development = self._get_weekly_development_activity(config.areas)
            sections["development_activity"] = development
        
        # 5. Market Forecast
        forecast = self._get_market_forecast(config.areas)
        sections["market_forecast"] = forecast
        
        return sections
    
    def _generate_neighborhood_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate detailed neighborhood report"""
        sections = {}
        
        for area in config.areas[:3]:  # Limit to 3 neighborhoods
            area_data = {}
            
            # Get comprehensive neighborhood data
            area_data["overview"] = self._get_neighborhood_overview(area)
            area_data["recent_sales"] = self._get_recent_sales_summary(area)
            area_data["permit_trends"] = self._get_permit_trends(area)
            area_data["investment_grade"] = self._calculate_neighborhood_grade(area)
            
            sections[area] = area_data
        
        return sections
    
    def _generate_investment_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate investment opportunities report"""
        sections = {}
        
        # 1. Market Conditions
        sections["market_conditions"] = self._assess_market_conditions(config.areas)
        
        # 2. Top Investment Opportunities
        sections["opportunities"] = self._find_investment_opportunities(
            config.areas,
            limit=config.max_opportunities
        )
        
        # 3. Risk Assessment
        sections["risk_assessment"] = self._assess_market_risks(config.areas)
        
        # 4. ROI Analysis
        sections["roi_analysis"] = self._analyze_roi_potential(config.areas)
        
        return sections
    
    def _generate_permit_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate permit activity report"""
        sections = {}
        
        for area in config.areas:
            permits_data = self.permits.search_permits_by_area(
                neighborhood=area,
                days_back=30
            )
            
            stats = self.permits.get_permit_statistics(permits_data)
            trends = self.permits.get_neighborhood_trends(area, months_back=6)
            
            sections[area] = {
                "summary": stats,
                "trends": trends,
                "major_projects": [
                    p for p in permits_data 
                    if p.get("estimated_cost", 0) > 100000
                ][:5]
            }
        
        return sections
    
    def _generate_custom_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate custom report based on specified sections"""
        sections = {}
        
        if not config.custom_sections:
            return {"error": "No custom sections specified"}
        
        for section in config.custom_sections:
            if section == "market_trends":
                sections["market_trends"] = self._get_market_overview(config.areas)
            elif section == "opportunities":
                sections["opportunities"] = self._get_todays_opportunities(config.areas, 10)
            elif section == "permits":
                sections["permits"] = self._get_recent_permit_activity(config.areas)
            elif section == "analytics":
                sections["analytics"] = self._get_usage_analytics()
            else:
                sections[section] = {"error": f"Unknown section: {section}"}
        
        return sections
    
    def _get_market_overview(self, areas: List[str]) -> Dict[str, Any]:
        """Get market overview for areas"""
        try:
            areas_str = ", ".join(areas[:3])  # Limit to 3 areas
            
            prompt = f"""
            Provide a concise Houston real estate market overview for {datetime.now().strftime('%B %d, %Y')}
            focusing on these areas: {areas_str}
            
            Include:
            - Current market conditions (buyer's/seller's market)
            - Average price trends
            - Inventory levels
            - Key factors affecting the market today
            
            Keep it brief and factual.
            """
            
            response = self.perplexity.query(prompt)
            
            if response.get("success"):
                return {
                    "summary": response.get("data"),
                    "areas_analyzed": areas,
                    "generated_at": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error("Failed to get market overview", error=str(e))
        
        return {"error": "Failed to generate market overview"}
    
    def _get_todays_opportunities(self, areas: List[str], limit: int) -> List[Dict[str, Any]]:
        """Find today's best opportunities"""
        try:
            # Search for opportunities
            criteria = {
                "neighborhoods": areas,
                "max_price": 1000000,  # Reasonable upper limit
                "distressed": True
            }
            
            results = self.search_engine.find_opportunities(
                criteria=criteria,
                limit=limit,
                sort_by="score"
            )
            
            opportunities = results.get("opportunities", [])
            
            # Format for report
            formatted = []
            for opp in opportunities[:limit]:
                formatted.append({
                    "address": opp.get("address", "Unknown"),
                    "estimated_price": opp.get("estimated_price"),
                    "match_score": opp.get("match_score"),
                    "key_features": opp.get("match_reasons", [])[:3],
                    "description": opp.get("description", "")[:200] + "..."
                })
            
            return formatted
            
        except Exception as e:
            logger.error("Failed to get opportunities", error=str(e))
            return []
    
    def _get_recent_permit_activity(self, areas: List[str]) -> Dict[str, Any]:
        """Get recent permit activity summary"""
        activity = {}
        
        try:
            for area in areas[:3]:  # Limit to 3 areas
                permits = self.permits.search_permits_by_area(
                    neighborhood=area,
                    days_back=7,  # Last week
                    min_value=10000  # Significant permits only
                )
                
                if permits:
                    activity[area] = {
                        "count": len(permits),
                        "total_value": sum(p.get("estimated_cost", 0) for p in permits),
                        "major_projects": [
                            {
                                "address": p.get("address"),
                                "type": p.get("permit_type"),
                                "value": p.get("estimated_cost")
                            }
                            for p in sorted(
                                permits,
                                key=lambda x: x.get("estimated_cost", 0),
                                reverse=True
                            )[:3]
                        ]
                    }
                else:
                    activity[area] = {
                        "count": 0,
                        "total_value": 0,
                        "major_projects": []
                    }
            
        except Exception as e:
            logger.error("Failed to get permit activity", error=str(e))
        
        return activity
    
    def _get_market_pulse(self, areas: List[str]) -> Dict[str, Any]:
        """Get quick market pulse indicators"""
        try:
            areas_str = ", ".join(areas[:3])
            
            prompt = f"""
            Quick Houston real estate pulse check for {areas_str}:
            
            Provide brief answers:
            1. Hot or Cold market?
            2. Rising or Falling prices?
            3. High or Low inventory?
            4. Best opportunity type right now?
            
            One line per answer.
            """
            
            response = self.perplexity.query(prompt)
            
            if response.get("success"):
                # Parse response into structured data
                lines = response.get("data", "").strip().split("\n")
                
                pulse = {
                    "market_temperature": "Unknown",
                    "price_direction": "Unknown",
                    "inventory_level": "Unknown",
                    "opportunity_type": "Unknown"
                }
                
                # Simple parsing
                for line in lines:
                    lower = line.lower()
                    if "hot" in lower or "cold" in lower:
                        pulse["market_temperature"] = "Hot" if "hot" in lower else "Cold"
                    elif "rising" in lower or "falling" in lower:
                        pulse["price_direction"] = "Rising" if "rising" in lower else "Falling"
                    elif "high" in lower or "low" in lower:
                        if "inventory" in lower:
                            pulse["inventory_level"] = "High" if "high" in lower else "Low"
                    elif "opportunity" in lower:
                        pulse["opportunity_type"] = line.strip()
                
                return pulse
            
        except Exception as e:
            logger.error("Failed to get market pulse", error=str(e))
        
        return {}
    
    def _get_usage_analytics(self) -> Dict[str, Any]:
        """Get platform usage analytics for internal tracking"""
        try:
            # Get today's stats
            today_stats = usage_tracker.get_daily_stats()
            
            # Get popular queries
            popular = usage_tracker.get_popular_queries(days=7, limit=5)
            
            # Get insights
            insights = usage_tracker.generate_insights()
            
            return {
                "daily_metrics": {
                    "queries_today": today_stats.get("total_queries", 0),
                    "cache_hit_rate": today_stats.get("cache_hit_rate", 0),
                    "avg_response_time": today_stats.get("average_response_time", 0),
                    "estimated_cost": today_stats.get("total_cost", 0)
                },
                "popular_searches": [
                    {"type": q["query_type"], "count": q["count"]}
                    for q in popular
                ],
                "key_insights": [
                    insight["message"]
                    for insight in insights.get("insights", [])
                    if insight.get("priority") in ["high", "medium"]
                ][:3]
            }
            
        except Exception as e:
            logger.error("Failed to get usage analytics", error=str(e))
            return {}
    
    def _get_week_in_review(self, areas: List[str]) -> Dict[str, Any]:
        """Generate week in review summary"""
        areas_str = ", ".join(areas[:3])
        
        prompt = f"""
        Houston real estate week in review for {areas_str}:
        
        Summarize:
        1. Major market movements
        2. Notable sales or listings
        3. Price trends
        4. Market sentiment
        
        Keep it concise and data-driven.
        """
        
        response = self.perplexity.query(prompt)
        
        return {
            "summary": response.get("data") if response.get("success") else "No data available",
            "period": f"{(datetime.now() - timedelta(days=7)).strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}"
        }
    
    def _get_weekly_opportunities(self, areas: List[str]) -> List[Dict[str, Any]]:
        """Get best opportunities from the past week"""
        # For now, reuse daily opportunities with extended timeframe
        return self._get_todays_opportunities(areas, limit=15)
    
    def _get_neighborhood_trends(self, areas: List[str]) -> Dict[str, Any]:
        """Get neighborhood trend analysis"""
        trends = {}
        
        for area in areas[:3]:
            try:
                # Get permit trends
                permit_trends = self.permits.get_neighborhood_trends(area, months_back=3)
                
                trends[area] = {
                    "permit_trend": permit_trends.get("trend", "Unknown"),
                    "monthly_avg_permits": permit_trends.get("monthly_average", 0),
                    "total_investment": permit_trends.get("total_investment", 0)
                }
                
            except Exception as e:
                logger.warning(f"Failed to get trends for {area}", error=str(e))
                trends[area] = {"error": "Data unavailable"}
        
        return trends
    
    def _get_weekly_development_activity(self, areas: List[str]) -> Dict[str, Any]:
        """Get weekly development activity summary"""
        activity = {}
        
        for area in areas[:3]:
            permits = self.permits.search_permits_by_area(
                neighborhood=area,
                days_back=7,
                min_value=50000
            )
            
            activity[area] = {
                "new_permits": len(permits),
                "total_investment": sum(p.get("estimated_cost", 0) for p in permits),
                "project_types": list(set(p.get("permit_type", "Unknown") for p in permits))[:5]
            }
        
        return activity
    
    def _get_market_forecast(self, areas: List[str]) -> Dict[str, Any]:
        """Generate market forecast"""
        areas_str = ", ".join(areas[:3])
        
        prompt = f"""
        30-day Houston real estate forecast for {areas_str}:
        
        Predict:
        1. Price direction and magnitude
        2. Inventory changes
        3. Market opportunities
        4. Potential risks
        
        Base on current trends and data.
        """
        
        response = self.perplexity.query(prompt)
        
        return {
            "forecast": response.get("data") if response.get("success") else "Forecast unavailable",
            "forecast_period": "Next 30 days",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_neighborhood_overview(self, area: str) -> Dict[str, Any]:
        """Get comprehensive neighborhood overview"""
        prompt = f"""
        Current overview of {area}, Houston real estate market:
        - Median home price
        - Average days on market
        - Inventory levels
        - Key characteristics
        - Recent trends
        """
        
        response = self.perplexity.query(prompt)
        
        return {
            "overview": response.get("data") if response.get("success") else "No data",
            "area": area
        }
    
    def _get_recent_sales_summary(self, area: str) -> Dict[str, Any]:
        """Get recent sales summary for area"""
        # For now, return placeholder
        # In production, this would query MLS or other data sources
        return {
            "message": "Recent sales data integration pending",
            "area": area
        }
    
    def _get_permit_trends(self, area: str) -> Dict[str, Any]:
        """Get permit trends for specific area"""
        try:
            return self.permits.get_neighborhood_trends(area, months_back=6)
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_neighborhood_grade(self, area: str) -> str:
        """Calculate investment grade for neighborhood"""
        # Simplified grading based on available data
        try:
            trends = self.permits.get_neighborhood_trends(area, months_back=6)
            
            if trends.get("trend") == "Increasing significantly":
                return "A - High growth area"
            elif trends.get("trend") == "Increasing":
                return "B - Growing area"
            elif trends.get("trend") == "Stable":
                return "C - Stable area"
            else:
                return "D - Declining or unknown"
                
        except Exception:
            return "Insufficient data"
    
    def _assess_market_conditions(self, areas: List[str]) -> Dict[str, Any]:
        """Assess current market conditions"""
        areas_str = ", ".join(areas[:3])
        
        prompt = f"""
        Assess current investment conditions in Houston {areas_str}:
        - Overall market strength (1-10)
        - Best property types for investment
        - Current risks
        - Opportunities
        """
        
        response = self.perplexity.query(prompt)
        
        return {
            "assessment": response.get("data") if response.get("success") else "Assessment unavailable",
            "areas": areas[:3],
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    
    def _find_investment_opportunities(self, areas: List[str], limit: int) -> List[Dict[str, Any]]:
        """Find investment opportunities with detailed analysis"""
        criteria = {
            "neighborhoods": areas,
            "max_price": 800000,
            "min_cap_rate": 6,
            "property_types": ["single-family", "multi-family", "condo"]
        }
        
        results = self.search_engine.find_opportunities(
            criteria=criteria,
            limit=limit,
            sort_by="score"
        )
        
        return results.get("opportunities", [])[:limit]
    
    def _assess_market_risks(self, areas: List[str]) -> Dict[str, Any]:
        """Assess market risks for areas"""
        areas_str = ", ".join(areas[:3])
        
        prompt = f"""
        Identify real estate investment risks in Houston {areas_str}:
        - Market risks
        - Environmental risks (flooding, etc.)
        - Economic factors
        - Development concerns
        
        Be specific and data-driven.
        """
        
        response = self.perplexity.query(prompt)
        
        return {
            "risk_assessment": response.get("data") if response.get("success") else "Risk assessment unavailable",
            "areas": areas[:3]
        }
    
    def _analyze_roi_potential(self, areas: List[str]) -> Dict[str, Any]:
        """Analyze ROI potential for areas"""
        areas_str = ", ".join(areas[:3])
        
        prompt = f"""
        Analyze ROI potential for Houston {areas_str}:
        - Average rental yields
        - Appreciation rates
        - Cap rates
        - Best investment strategies
        """
        
        response = self.perplexity.query(prompt)
        
        return {
            "roi_analysis": response.get("data") if response.get("success") else "ROI analysis unavailable",
            "areas": areas[:3]
        }
    
    def _get_report_title(self, config: ReportConfig) -> str:
        """Generate report title based on type and date"""
        date_str = datetime.now().strftime("%B %d, %Y")
        
        if config.report_type == ReportType.DAILY_MARKET:
            return f"HDI Daily Market Report - {date_str}"
        elif config.report_type == ReportType.WEEKLY_SUMMARY:
            return f"HDI Weekly Market Summary - Week of {date_str}"
        elif config.report_type == ReportType.NEIGHBORHOOD_FOCUS:
            areas = ", ".join(config.areas[:2])
            return f"HDI Neighborhood Report: {areas} - {date_str}"
        elif config.report_type == ReportType.INVESTMENT_OPPORTUNITIES:
            return f"HDI Investment Opportunities Report - {date_str}"
        elif config.report_type == ReportType.PERMIT_ACTIVITY:
            return f"HDI Permit Activity Report - {date_str}"
        else:
            return f"HDI Custom Report - {date_str}"
    
    def _format_as_markdown(self, report: Dict[str, Any]) -> str:
        """Format report as markdown"""
        md = f"# {report['title']}\n\n"
        md += f"*Generated: {report['generated_at']}*\n\n"
        
        for section_name, section_data in report["sections"].items():
            md += f"## {section_name.replace('_', ' ').title()}\n\n"
            
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if isinstance(value, list):
                        md += f"**{key.replace('_', ' ').title()}:**\n"
                        for item in value:
                            md += f"- {item}\n"
                        md += "\n"
                    elif isinstance(value, dict):
                        md += f"**{key.replace('_', ' ').title()}:**\n"
                        md += "```json\n"
                        md += json.dumps(value, indent=2)
                        md += "\n```\n\n"
                    else:
                        md += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
            else:
                md += f"{section_data}\n\n"
        
        return md
    
    def _format_as_html(self, report: Dict[str, Any]) -> str:
        """Format report as HTML"""
        # Simple HTML formatting - in production this would use templates
        html = f"""
        <html>
        <head>
            <title>{report['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
                .section {{ margin-bottom: 30px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f5f5f5; }}
                pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>{report['title']}</h1>
            <p><em>Generated: {report['generated_at']}</em></p>
        """
        
        for section_name, section_data in report["sections"].items():
            html += f'<div class="section">'
            html += f'<h2>{section_name.replace("_", " ").title()}</h2>'
            
            if isinstance(section_data, dict):
                html += self._dict_to_html(section_data)
            else:
                html += f'<p>{section_data}</p>'
            
            html += '</div>'
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _dict_to_html(self, data: Dict[str, Any], level: int = 0) -> str:
        """Convert dictionary to HTML"""
        html = ""
        
        for key, value in data.items():
            if isinstance(value, dict):
                html += f'<h{3+level}>{key.replace("_", " ").title()}</h{3+level}>'
                html += self._dict_to_html(value, level + 1)
            elif isinstance(value, list):
                html += f'<h{3+level}>{key.replace("_", " ").title()}</h{3+level}>'
                html += '<ul>'
                for item in value:
                    if isinstance(item, dict):
                        html += '<li>' + str(item) + '</li>'
                    else:
                        html += f'<li>{item}</li>'
                html += '</ul>'
            else:
                html += f'<div class="metric"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
        
        return html