"""Automated reports API endpoints"""

from flask import request, g
from flask_restx import Namespace, Resource, fields
from datetime import datetime

from backend.services.report_generator import ReportGenerator, ReportConfig, ReportType
from backend.utils.exceptions import ValidationError

reports_ns = Namespace("reports", description="Automated report generation")

# Request/Response models
report_config_model = reports_ns.model("ReportConfig", {
    "report_type": fields.String(
        required=True,
        description="Type of report",
        enum=["daily_market", "weekly_summary", "neighborhood_focus", 
              "investment_opportunities", "permit_activity", "custom"]
    ),
    "areas": fields.List(
        fields.String,
        required=True,
        description="List of neighborhoods or ZIP codes",
        min_items=1
    ),
    "include_permits": fields.Boolean(
        default=True,
        description="Include permit data in report"
    ),
    "include_opportunities": fields.Boolean(
        default=True,
        description="Include investment opportunities"
    ),
    "include_analytics": fields.Boolean(
        default=True,
        description="Include platform analytics (internal)"
    ),
    "custom_sections": fields.List(
        fields.String,
        description="Custom sections for custom report type"
    ),
    "max_opportunities": fields.Integer(
        default=10,
        description="Maximum number of opportunities to include"
    )
})

report_schedule_model = reports_ns.model("ReportSchedule", {
    "config": fields.Nested(report_config_model, required=True),
    "schedule": fields.String(
        required=True,
        description="Schedule frequency",
        enum=["daily", "weekly", "monthly", "once"]
    ),
    "delivery_method": fields.String(
        default="api",
        description="How to deliver the report",
        enum=["api", "email", "slack"]
    ),
    "delivery_config": fields.Raw(
        description="Delivery configuration (email address, slack channel, etc.)"
    )
})

report_response_model = reports_ns.model("ReportResponse", {
    "report_id": fields.String(description="Unique report ID"),
    "title": fields.String(description="Report title"),
    "generated_at": fields.DateTime(description="Generation timestamp"),
    "type": fields.String(description="Report type"),
    "areas": fields.List(fields.String, description="Areas covered"),
    "sections": fields.Raw(description="Report sections"),
    "metadata": fields.Raw(description="Report metadata"),
    "format": fields.String(description="Output format")
})

@reports_ns.route("/generate")
class GenerateReport(Resource):
    """Generate a report on demand"""
    
    @reports_ns.doc("generate_report")
    @reports_ns.expect(report_config_model)
    @reports_ns.param("format", "Output format (json, markdown, html)", default="json")
    @reports_ns.marshal_with(report_response_model)
    def post(self):
        """Generate a new report based on configuration"""
        data = request.json
        format_type = request.args.get("format", "json")
        
        # Validate report type
        try:
            report_type = ReportType(data["report_type"])
        except ValueError:
            raise ValidationError(f"Invalid report type: {data['report_type']}")
        
        # Validate areas
        if not data.get("areas"):
            raise ValidationError("At least one area is required")
        
        if len(data["areas"]) > 5:
            raise ValidationError("Maximum 5 areas allowed per report")
        
        # Create report config
        config = ReportConfig(
            report_type=report_type,
            areas=data["areas"],
            include_permits=data.get("include_permits", True),
            include_opportunities=data.get("include_opportunities", True),
            include_analytics=data.get("include_analytics", True),
            custom_sections=data.get("custom_sections"),
            max_opportunities=data.get("max_opportunities", 10)
        )
        
        # Generate report
        generator = ReportGenerator()
        report = generator.generate_report(config, format=format_type)
        
        # Add report ID for tracking
        report["report_id"] = f"rpt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        report["format"] = format_type
        
        # Track usage
        g.query_cost = 0.004 * len(config.areas)  # Estimate based on areas
        
        return report

@reports_ns.route("/types")
class ReportTypes(Resource):
    """Get available report types"""
    
    @reports_ns.doc("get_report_types")
    def get(self):
        """Get list of available report types with descriptions"""
        return {
            "report_types": [
                {
                    "type": "daily_market",
                    "name": "Daily Market Report",
                    "description": "Daily summary of market conditions, opportunities, and permit activity",
                    "typical_sections": ["market_overview", "opportunities", "permit_activity", "market_pulse"],
                    "recommended_schedule": "daily"
                },
                {
                    "type": "weekly_summary",
                    "name": "Weekly Market Summary",
                    "description": "Comprehensive weekly review with trends and forecasts",
                    "typical_sections": ["week_in_review", "top_opportunities", "neighborhood_trends", "development_activity", "market_forecast"],
                    "recommended_schedule": "weekly"
                },
                {
                    "type": "neighborhood_focus",
                    "name": "Neighborhood Deep Dive",
                    "description": "Detailed analysis of specific neighborhoods",
                    "typical_sections": ["overview", "recent_sales", "permit_trends", "investment_grade"],
                    "recommended_schedule": "monthly"
                },
                {
                    "type": "investment_opportunities",
                    "name": "Investment Opportunities Report",
                    "description": "Focused report on investment opportunities and ROI analysis",
                    "typical_sections": ["market_conditions", "opportunities", "risk_assessment", "roi_analysis"],
                    "recommended_schedule": "weekly"
                },
                {
                    "type": "permit_activity",
                    "name": "Permit Activity Report",
                    "description": "Construction and renovation activity analysis",
                    "typical_sections": ["summary", "trends", "major_projects"],
                    "recommended_schedule": "weekly"
                },
                {
                    "type": "custom",
                    "name": "Custom Report",
                    "description": "Build your own report with selected sections",
                    "available_sections": ["market_trends", "opportunities", "permits", "analytics"],
                    "recommended_schedule": "as_needed"
                }
            ]
        }

@reports_ns.route("/preview")
class PreviewReport(Resource):
    """Preview report sections"""
    
    @reports_ns.doc("preview_report")
    @reports_ns.expect(report_config_model)
    def post(self):
        """Preview what sections will be included in a report"""
        data = request.json
        
        try:
            report_type = ReportType(data["report_type"])
        except ValueError:
            raise ValidationError(f"Invalid report type: {data['report_type']}")
        
        # Map report types to their sections
        section_map = {
            ReportType.DAILY_MARKET: [
                "market_overview",
                "opportunities" if data.get("include_opportunities", True) else None,
                "permit_activity" if data.get("include_permits", True) else None,
                "market_pulse",
                "platform_analytics" if data.get("include_analytics", True) else None
            ],
            ReportType.WEEKLY_SUMMARY: [
                "week_in_review",
                "top_opportunities" if data.get("include_opportunities", True) else None,
                "neighborhood_trends",
                "development_activity" if data.get("include_permits", True) else None,
                "market_forecast"
            ],
            ReportType.NEIGHBORHOOD_FOCUS: [
                f"{area}_overview" for area in data.get("areas", [])[:3]
            ],
            ReportType.INVESTMENT_OPPORTUNITIES: [
                "market_conditions",
                "opportunities",
                "risk_assessment",
                "roi_analysis"
            ],
            ReportType.PERMIT_ACTIVITY: [
                f"{area}_permits" for area in data.get("areas", [])
            ],
            ReportType.CUSTOM: data.get("custom_sections", [])
        }
        
        sections = [s for s in section_map.get(report_type, []) if s is not None]
        
        return {
            "report_type": report_type.value,
            "areas": data.get("areas", []),
            "sections": sections,
            "estimated_generation_time": len(sections) * 2,  # Rough estimate in seconds
            "estimated_cost": 0.004 * len(data.get("areas", []))
        }

@reports_ns.route("/schedule")
class ScheduleReport(Resource):
    """Schedule recurring reports"""
    
    @reports_ns.doc("schedule_report")
    @reports_ns.expect(report_schedule_model)
    def post(self):
        """Schedule a recurring report (placeholder - not implemented)"""
        data = request.json
        
        # For now, return a mock response
        # In production, this would integrate with a task scheduler
        return {
            "schedule_id": f"sch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "status": "scheduled",
            "config": data["config"],
            "schedule": data["schedule"],
            "next_run": datetime.utcnow().isoformat(),
            "message": "Report scheduling is a placeholder feature - not yet implemented"
        }

@reports_ns.route("/templates")
class ReportTemplates(Resource):
    """Get report templates"""
    
    @reports_ns.doc("get_report_templates")
    def get(self):
        """Get pre-configured report templates for common use cases"""
        return {
            "templates": [
                {
                    "name": "Heights & Montrose Daily Brief",
                    "description": "Daily market update for popular inner-loop neighborhoods",
                    "config": {
                        "report_type": "daily_market",
                        "areas": ["Houston Heights", "Montrose", "River Oaks"],
                        "include_permits": True,
                        "include_opportunities": True,
                        "include_analytics": False,
                        "max_opportunities": 5
                    }
                },
                {
                    "name": "Investment Hotspots Weekly",
                    "description": "Weekly investment opportunity scan across emerging areas",
                    "config": {
                        "report_type": "investment_opportunities",
                        "areas": ["East End", "Third Ward", "Acres Homes", "Sunnyside"],
                        "include_permits": True,
                        "include_opportunities": True,
                        "max_opportunities": 15
                    }
                },
                {
                    "name": "Luxury Market Analysis",
                    "description": "High-end property market analysis",
                    "config": {
                        "report_type": "neighborhood_focus",
                        "areas": ["River Oaks", "Memorial", "Tanglewood"],
                        "include_permits": True,
                        "include_opportunities": True
                    }
                },
                {
                    "name": "Development Activity Tracker",
                    "description": "Weekly construction and renovation activity report",
                    "config": {
                        "report_type": "permit_activity",
                        "areas": ["Downtown", "Midtown", "EaDo", "Washington Ave"],
                        "include_permits": True
                    }
                }
            ]
        }