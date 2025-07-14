#!/usr/bin/env python3
"""HDI Command Line Interface for quick property searches"""

import sys
import os
import argparse
import json
import requests
from datetime import datetime
from typing import List, Optional
from tabulate import tabulate

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Default API endpoint
DEFAULT_API_URL = "http://localhost:5000/api/v1"

class HDICli:
    """Command line interface for HDI"""
    
    def __init__(self, api_url: str = DEFAULT_API_URL):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
    
    def search(self, query: str) -> None:
        """Natural language property search"""
        print(f"🔍 Searching: {query}\n")
        
        try:
            response = self.session.post(
                f"{self.api_url}/query",
                json={"query": query}
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                print(data.get("data", "No results found"))
                
                # Show metadata
                metadata = data.get("metadata", {})
                if metadata:
                    print(f"\n📊 Query Stats:")
                    print(f"  Response time: {metadata.get('response_time', 0):.2f}s")
                    print(f"  Cost: ${metadata.get('cost', 0):.4f}")
            else:
                print("❌ Search failed")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def analyze(self, address: str) -> None:
        """Analyze a specific property"""
        print(f"🏠 Analyzing: {address}\n")
        
        try:
            response = self.session.get(
                f"{self.api_url}/properties/analyze",
                params={"address": address}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Show official data if available
            if data.get("official_data"):
                print("📋 Official Data (HCAD):")
                official = data["official_data"]
                if "appraised_value" in official:
                    print(f"  Appraised Value: {official['appraised_value']}")
                if "year_built" in official:
                    print(f"  Year Built: {official['year_built']}")
                if "living_area" in official:
                    print(f"  Living Area: {official['living_area']}")
                print()
            
            # Show market insights
            if data.get("market_insights"):
                print("📈 Market Insights:")
                insights = data["market_insights"]
                # Truncate long insights
                if len(insights) > 500:
                    print(f"  {insights[:500]}...")
                else:
                    print(f"  {insights}")
                print()
            
            # Show recommendations
            if data.get("recommendations"):
                print("💡 Recommendations:")
                for rec in data["recommendations"]:
                    print(f"  • {rec}")
                print()
            
            # Show confidence score
            print(f"🎯 Confidence Score: {data.get('confidence_score', 0):.1%}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def compare(self, addresses: List[str]) -> None:
        """Compare multiple properties"""
        print(f"⚖️  Comparing {len(addresses)} properties\n")
        
        try:
            response = self.session.get(
                f"{self.api_url}/bulk/compare",
                params={"addresses": ",".join(addresses)}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Show summary
            if data.get("summary"):
                summary = data["summary"]
                print("📊 Summary:")
                if "value_statistics" in summary:
                    stats = summary["value_statistics"]
                    print(f"  Total Value: ${stats.get('total_value', 0):,.0f}")
                    print(f"  Average Value: ${stats.get('average_value', 0):,.0f}")
                    print(f"  Range: ${stats.get('min_value', 0):,.0f} - ${stats.get('max_value', 0):,.0f}")
                print()
            
            # Show rankings
            if data.get("rankings"):
                print("🏆 Rankings:")
                for ranking in data["rankings"]:
                    print(f"\n  {ranking['criteria']}:")
                    for prop in ranking["ranked_properties"][:5]:  # Top 5
                        print(f"    {prop['rank']}. {prop['address']}")
                        if "score" in prop:
                            print(f"       Score: {prop['score']}")
                        if "value" in prop:
                            print(f"       Value: {prop['value']}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def market(self, area: str) -> None:
        """Get market trends for an area"""
        print(f"📈 Market Analysis: {area}\n")
        
        try:
            response = self.session.get(
                f"{self.api_url}/market/trends",
                params={"area": area}
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                print(data.get("data", "No market data available"))
            else:
                print("❌ Failed to get market data")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def stats(self) -> None:
        """Show usage statistics"""
        print("📊 HDI Usage Statistics\n")
        
        try:
            # Get today's stats
            response = self.session.get(f"{self.api_url}/analytics/stats/daily")
            response.raise_for_status()
            today_stats = response.json()
            
            print("Today's Stats:")
            print(f"  Total Queries: {today_stats.get('total_queries', 0)}")
            print(f"  Cache Hit Rate: {today_stats.get('cache_hit_rate', 0):.1%}")
            print(f"  Total Cost: ${today_stats.get('total_cost', 0):.2f}")
            print(f"  Avg Response Time: {today_stats.get('average_response_time', 0):.2f}s")
            print()
            
            # Get insights
            response = self.session.get(f"{self.api_url}/analytics/insights")
            response.raise_for_status()
            insights_data = response.json()
            
            if insights_data.get("insights"):
                print("💡 Insights:")
                for insight in insights_data["insights"][:3]:  # Top 3
                    icon = "⚠️" if insight["priority"] == "high" else "ℹ️"
                    print(f"  {icon} {insight['message']}")
            
        except Exception as e:
            print(f"❌ Error getting stats: {str(e)}")
    
    def bulk(self, addresses_file: str, analysis_type: str = "standard") -> None:
        """Bulk analyze properties from a file"""
        try:
            # Read addresses from file
            with open(addresses_file, 'r') as f:
                addresses = [line.strip() for line in f if line.strip()]
            
            if not addresses:
                print("❌ No addresses found in file")
                return
            
            print(f"📦 Bulk analyzing {len(addresses)} properties ({analysis_type} mode)\n")
            
            # Call bulk API
            response = self.session.post(
                f"{self.api_url}/bulk/analyze",
                json={
                    "addresses": addresses,
                    "analysis_type": analysis_type,
                    "include_comparisons": True
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Show results
            print(f"✅ Completed in {data.get('processing_time', 0):.1f} seconds")
            print(f"   Successful: {data.get('successful_analyses', 0)}/{data.get('total_properties', 0)}")
            
            # Show opportunities
            if data.get("opportunities"):
                print(f"\n🎯 Found {len(data['opportunities'])} opportunities:")
                for opp in data["opportunities"][:5]:  # Top 5
                    print(f"  • {opp['address']}: {opp['reason']}")
            
            # Save results
            output_file = addresses_file.replace('.txt', '_results.json')
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n📁 Full results saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def report(self, report_type: str, areas: List[str], format_type: str = "json", 
               save: bool = False, no_permits: bool = False, no_opportunities: bool = False,
               include_analytics: bool = False, max_opportunities: int = 10) -> None:
        """Generate an automated report"""
        print(f"📊 Generating {report_type} report for {', '.join(areas)}\n")
        
        config = {
            "report_type": report_type,
            "areas": areas,
            "include_permits": not no_permits,
            "include_opportunities": not no_opportunities,
            "include_analytics": include_analytics,
            "max_opportunities": max_opportunities
        }
        
        try:
            response = self.session.post(
                f"{self.api_url}/reports/generate",
                json=config,
                params={"format": format_type}
            )
            response.raise_for_status()
            
            if format_type == "json":
                report = response.json()
                print(f"✅ {report['title']}")
                print(f"   Generated: {report['generated_at']}")
                print(f"   Report ID: {report['report_id']}")
                print(f"   Sections: {len(report['sections'])}")
                
                # Show section summaries
                for section_name, section_data in report['sections'].items():
                    print(f"\n📌 {section_name.replace('_', ' ').title()}:")
                    if isinstance(section_data, dict):
                        for key in list(section_data.keys())[:2]:  # First 2 keys
                            print(f"    - {key}")
                    elif isinstance(section_data, list):
                        print(f"    - {len(section_data)} items")
                    else:
                        print(f"    - {str(section_data)[:100]}...")
                
                # Save if requested
                if save:
                    filename = f"{report['report_id']}.json"
                    with open(filename, 'w') as f:
                        json.dump(report, f, indent=2)
                    print(f"\n💾 Report saved to: {filename}")
                    
            else:
                # Markdown or HTML format
                content = response.text
                print(f"✅ Report generated ({len(content)} characters)")
                
                if save:
                    ext = "md" if format_type == "markdown" else "html"
                    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                    with open(filename, 'w') as f:
                        f.write(content)
                    print(f"\n💾 Report saved to: {filename}")
                else:
                    # Show preview
                    print("\nPreview (first 300 chars):")
                    print(content[:300] + "...")
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def report_types(self) -> None:
        """Show available report types"""
        print("📋 Available Report Types\n")
        
        try:
            response = self.session.get(f"{self.api_url}/reports/types")
            response.raise_for_status()
            
            data = response.json()
            for report_type in data["report_types"]:
                print(f"📊 {report_type['name']} ({report_type['type']})")
                print(f"   {report_type['description']}")
                print(f"   Recommended schedule: {report_type['recommended_schedule']}")
                print()
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def report_templates(self) -> None:
        """Show available report templates"""
        print("📄 Report Templates\n")
        
        try:
            response = self.session.get(f"{self.api_url}/reports/templates")
            response.raise_for_status()
            
            data = response.json()
            for template in data["templates"]:
                print(f"📄 {template['name']}")
                print(f"   {template['description']}")
                print(f"   Areas: {', '.join(template['config']['areas'])}")
                print(f"   Type: {template['config']['report_type']}")
                print()
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="HDI - Houston Data Intelligence CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hdi search "3bed 2bath under 400k in Heights"
  hdi analyze "1234 Main St, Houston, TX"
  hdi compare "1000 Main St" "2000 Bagby St" "3000 Post Oak"
  hdi market "Houston Heights"
  hdi stats
  hdi bulk addresses.txt --type investment
  hdi report daily_market "Heights,Montrose" --save
  hdi report-types
  hdi report-templates
        """
    )
    
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="API endpoint URL"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Natural language property search")
    search_parser.add_argument("query", help="Search query")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a specific property")
    analyze_parser.add_argument("address", help="Property address")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare multiple properties")
    compare_parser.add_argument("addresses", nargs="+", help="Property addresses to compare")
    
    # Market command
    market_parser = subparsers.add_parser("market", help="Get market trends for an area")
    market_parser.add_argument("area", help="Area name (e.g., 'Houston Heights')")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show usage statistics")
    
    # Bulk command
    bulk_parser = subparsers.add_parser("bulk", help="Bulk analyze properties from file")
    bulk_parser.add_argument("file", help="File containing addresses (one per line)")
    bulk_parser.add_argument("--type", choices=["standard", "quick", "investment"], 
                           default="standard", help="Analysis type")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate automated report")
    report_parser.add_argument("type", choices=["daily_market", "weekly_summary", 
                               "neighborhood_focus", "investment_opportunities", 
                               "permit_activity", "custom"],
                              help="Report type")
    report_parser.add_argument("areas", help="Comma-separated areas/neighborhoods")
    report_parser.add_argument("--format", choices=["json", "markdown", "html"],
                              default="json", help="Output format")
    report_parser.add_argument("--save", action="store_true", help="Save report to file")
    report_parser.add_argument("--no-permits", action="store_true", 
                              help="Exclude permit data")
    report_parser.add_argument("--no-opportunities", action="store_true",
                              help="Exclude opportunities")
    report_parser.add_argument("--include-analytics", action="store_true",
                              help="Include platform analytics")
    report_parser.add_argument("--max-opportunities", type=int, default=10,
                              help="Maximum opportunities to include")
    
    # Report types command
    types_parser = subparsers.add_parser("report-types", help="Show available report types")
    
    # Report templates command
    templates_parser = subparsers.add_parser("report-templates", help="Show report templates")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = HDICli(args.api_url)
    
    # Execute command
    if args.command == "search":
        cli.search(args.query)
    elif args.command == "analyze":
        cli.analyze(args.address)
    elif args.command == "compare":
        cli.compare(args.addresses)
    elif args.command == "market":
        cli.market(args.area)
    elif args.command == "stats":
        cli.stats()
    elif args.command == "bulk":
        cli.bulk(args.file, args.type)
    elif args.command == "report":
        areas = [area.strip() for area in args.areas.split(',')]
        cli.report(args.type, areas, args.format, args.save, args.no_permits,
                  args.no_opportunities, args.include_analytics, args.max_opportunities)
    elif args.command == "report-types":
        cli.report_types()
    elif args.command == "report-templates":
        cli.report_templates()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()