"""Houston building permits data client"""

import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
from urllib.parse import quote

from backend.config.settings import settings
from backend.utils.exceptions import HDIException

logger = structlog.get_logger(__name__)

class PermitsClient:
    """Client for Houston building permits data"""
    
    # Houston Open Data Portal API endpoint
    PERMITS_API_URL = "https://data.houstontx.gov/api/id/76eh-xm7e.json"
    DATASET_ID = "76eh-xm7e"  # Building permits dataset
    
    def __init__(self):
        """Initialize permits client"""
        self.session = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "HDI Houston Data Intelligence",
                "Accept": "application/json"
            }
        )
        logger.info("PermitsClient initialized")
    
    def search_permits_by_address(
        self,
        address: str,
        days_back: int = 365,
        permit_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for permits by address
        
        Args:
            address: Property address
            days_back: Number of days to look back (default: 365)
            permit_types: List of permit types to filter (optional)
            
        Returns:
            List of permits
        """
        try:
            logger.info("Searching permits by address", address=address, days_back=days_back)
            
            # Clean address for search
            clean_address = self._clean_address(address)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Build query
            params = {
                "select": "*",
                "limit": 1000,
                "where": f"address like '%{clean_address}%'"
            }
            
            # Add date filter
            date_filter = f" AND issue_date >= '{start_date.strftime('%Y-%m-%d')}'"
            params["where"] += date_filter
            
            # Add permit type filter if specified
            if permit_types:
                types_filter = " AND (" + " OR ".join([f"permit_type = '{pt}'" for pt in permit_types]) + ")"
                params["where"] += types_filter
            
            # Make request
            response = self._make_request(params)
            
            # Parse and enhance results
            permits = self._parse_permits(response)
            
            logger.info(f"Found {len(permits)} permits", address=address)
            return permits
            
        except Exception as e:
            logger.error("Permit search failed", error=str(e), address=address)
            raise HDIException(f"Failed to search permits: {str(e)}")
    
    def search_permits_by_area(
        self,
        zip_code: Optional[str] = None,
        neighborhood: Optional[str] = None,
        days_back: int = 90,
        min_value: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for permits in an area
        
        Args:
            zip_code: ZIP code to search
            neighborhood: Neighborhood name
            days_back: Number of days to look back
            min_value: Minimum permit value
            
        Returns:
            List of permits
        """
        try:
            logger.info(
                "Searching permits by area",
                zip_code=zip_code,
                neighborhood=neighborhood,
                days_back=days_back
            )
            
            # Build location filter
            where_clauses = []
            
            if zip_code:
                where_clauses.append(f"zip_code = '{zip_code}'")
            
            if neighborhood:
                where_clauses.append(f"neighborhood like '%{neighborhood}%'")
            
            if not where_clauses:
                raise ValueError("Either zip_code or neighborhood must be provided")
            
            # Build query
            params = {
                "select": "*",
                "limit": 1000,
                "where": " OR ".join(where_clauses)
            }
            
            # Add date filter
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            params["where"] = f"({params['where']}) AND issue_date >= '{start_date.strftime('%Y-%m-%d')}'"
            
            # Add value filter
            if min_value:
                params["where"] += f" AND estimated_cost >= {min_value}"
            
            # Make request
            response = self._make_request(params)
            
            # Parse results
            permits = self._parse_permits(response)
            
            logger.info(f"Found {len(permits)} area permits")
            return permits
            
        except Exception as e:
            logger.error("Area permit search failed", error=str(e))
            raise HDIException(f"Failed to search area permits: {str(e)}")
    
    def get_permit_statistics(
        self,
        permits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate statistics from permit data
        
        Args:
            permits: List of permits
            
        Returns:
            Statistics dictionary
        """
        if not permits:
            return {
                "total_permits": 0,
                "total_value": 0,
                "average_value": 0,
                "permit_types": {},
                "recent_activity": "No recent permits"
            }
        
        # Calculate basic stats
        total_value = sum(p.get("estimated_cost", 0) for p in permits)
        
        # Count by type
        type_counts = {}
        for permit in permits:
            permit_type = permit.get("permit_type", "Unknown")
            type_counts[permit_type] = type_counts.get(permit_type, 0) + 1
        
        # Find most recent
        sorted_permits = sorted(
            permits,
            key=lambda p: p.get("issue_date", ""),
            reverse=True
        )
        most_recent = sorted_permits[0] if sorted_permits else None
        
        # Determine activity level
        recent_count = sum(
            1 for p in permits
            if self._is_recent(p.get("issue_date"), days=90)
        )
        
        if recent_count >= 10:
            activity_level = "Very high permit activity"
        elif recent_count >= 5:
            activity_level = "High permit activity"
        elif recent_count >= 2:
            activity_level = "Moderate permit activity"
        elif recent_count >= 1:
            activity_level = "Some recent permit activity"
        else:
            activity_level = "Low permit activity"
        
        return {
            "total_permits": len(permits),
            "total_value": total_value,
            "average_value": total_value / len(permits) if permits else 0,
            "permit_types": type_counts,
            "most_recent_permit": most_recent,
            "recent_activity": activity_level,
            "recent_count_90_days": recent_count,
            "major_renovations": sum(
                1 for p in permits
                if p.get("estimated_cost", 0) > 50000
            ),
            "new_construction": sum(
                1 for p in permits
                if "new" in p.get("permit_type", "").lower()
            )
        }
    
    def get_neighborhood_trends(
        self,
        neighborhood: str,
        months_back: int = 12
    ) -> Dict[str, Any]:
        """
        Get permit trends for a neighborhood
        
        Args:
            neighborhood: Neighborhood name
            months_back: Number of months to analyze
            
        Returns:
            Trend analysis
        """
        try:
            # Get permits for the period
            permits = self.search_permits_by_area(
                neighborhood=neighborhood,
                days_back=months_back * 30
            )
            
            if not permits:
                return {
                    "neighborhood": neighborhood,
                    "trend": "No permit data available",
                    "monthly_average": 0,
                    "total_investment": 0
                }
            
            # Group by month
            monthly_data = {}
            for permit in permits:
                issue_date = permit.get("issue_date", "")
                if issue_date:
                    month_key = issue_date[:7]  # YYYY-MM
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {
                            "count": 0,
                            "value": 0
                        }
                    monthly_data[month_key]["count"] += 1
                    monthly_data[month_key]["value"] += permit.get("estimated_cost", 0)
            
            # Calculate trends
            months = sorted(monthly_data.keys())
            if len(months) >= 3:
                # Compare recent 3 months to previous 3 months
                recent_months = months[-3:]
                previous_months = months[-6:-3] if len(months) >= 6 else months[:-3]
                
                recent_avg = sum(monthly_data[m]["count"] for m in recent_months) / 3
                previous_avg = sum(monthly_data[m]["count"] for m in previous_months) / len(previous_months) if previous_months else 0
                
                if previous_avg > 0:
                    trend_pct = ((recent_avg - previous_avg) / previous_avg) * 100
                    if trend_pct > 20:
                        trend = "Increasing significantly"
                    elif trend_pct > 5:
                        trend = "Increasing"
                    elif trend_pct < -20:
                        trend = "Decreasing significantly"
                    elif trend_pct < -5:
                        trend = "Decreasing"
                    else:
                        trend = "Stable"
                else:
                    trend = "New activity"
            else:
                trend = "Insufficient data for trend"
            
            # Calculate statistics
            total_investment = sum(p.get("estimated_cost", 0) for p in permits)
            monthly_average = len(permits) / months_back if months_back > 0 else 0
            
            return {
                "neighborhood": neighborhood,
                "trend": trend,
                "monthly_average": monthly_average,
                "total_investment": total_investment,
                "monthly_breakdown": monthly_data,
                "permit_count": len(permits),
                "months_analyzed": months_back,
                "top_permit_types": self._get_top_permit_types(permits, top_n=5)
            }
            
        except Exception as e:
            logger.error("Failed to get neighborhood trends", error=str(e))
            return {
                "neighborhood": neighborhood,
                "error": str(e)
            }
    
    def _make_request(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Make request to Houston data portal"""
        try:
            response = self.session.get(
                self.PERMITS_API_URL,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Houston data portal returns array directly
            if isinstance(data, list):
                return data
            else:
                logger.warning("Unexpected response format", data_type=type(data))
                return []
                
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error from permits API", status=e.response.status_code)
            raise HDIException(f"Permits API error: {e.response.status_code}")
        except Exception as e:
            logger.error("Permits API request failed", error=str(e))
            raise HDIException(f"Failed to fetch permits: {str(e)}")
    
    def _parse_permits(self, raw_permits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse and enhance permit data"""
        parsed_permits = []
        
        for permit in raw_permits:
            parsed = {
                "permit_number": permit.get("permit_number", ""),
                "permit_type": permit.get("permit_type", ""),
                "description": permit.get("description", ""),
                "address": permit.get("address", ""),
                "zip_code": permit.get("zip_code", ""),
                "neighborhood": permit.get("neighborhood", ""),
                "issue_date": permit.get("issue_date", ""),
                "estimated_cost": self._parse_cost(permit.get("estimated_cost", 0)),
                "status": permit.get("status", ""),
                "contractor": permit.get("contractor_name", ""),
                "owner": permit.get("owner_name", ""),
                "work_description": permit.get("work_description", ""),
                "source": "Houston Permits"
            }
            
            # Add derived fields
            parsed["is_major_renovation"] = parsed["estimated_cost"] > 50000
            parsed["is_new_construction"] = "new" in parsed["permit_type"].lower()
            parsed["days_ago"] = self._calculate_days_ago(parsed["issue_date"])
            
            parsed_permits.append(parsed)
        
        return parsed_permits
    
    def _clean_address(self, address: str) -> str:
        """Clean address for search"""
        # Remove common suffixes
        address = address.upper()
        address = address.replace(", HOUSTON", "")
        address = address.replace(", TX", "")
        address = address.replace(", TEXAS", "")
        
        # Extract street number and name
        parts = address.split()
        if parts:
            # Keep first few parts (number and street name)
            clean_parts = []
            for part in parts[:3]:  # Usually covers "1234 MAIN ST"
                if part not in ["APT", "UNIT", "SUITE", "#"]:
                    clean_parts.append(part)
                else:
                    break
            
            return " ".join(clean_parts)
        
        return address
    
    def _parse_cost(self, cost_value: Any) -> float:
        """Parse cost value to float"""
        if isinstance(cost_value, (int, float)):
            return float(cost_value)
        
        if isinstance(cost_value, str):
            # Remove $ and commas
            clean_value = cost_value.replace("$", "").replace(",", "")
            try:
                return float(clean_value)
            except ValueError:
                return 0.0
        
        return 0.0
    
    def _calculate_days_ago(self, date_str: str) -> Optional[int]:
        """Calculate how many days ago a date was"""
        if not date_str:
            return None
        
        try:
            # Parse date (assuming YYYY-MM-DD format)
            date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            delta = datetime.now() - date
            return delta.days
        except Exception:
            return None
    
    def _is_recent(self, date_str: str, days: int = 90) -> bool:
        """Check if date is within specified days"""
        days_ago = self._calculate_days_ago(date_str)
        return days_ago is not None and days_ago <= days
    
    def _get_top_permit_types(self, permits: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get most common permit types"""
        type_counts = {}
        
        for permit in permits:
            permit_type = permit.get("permit_type", "Unknown")
            type_counts[permit_type] = type_counts.get(permit_type, 0) + 1
        
        # Sort by count
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"type": ptype, "count": count}
            for ptype, count in sorted_types[:top_n]
        ]
    
    def close(self):
        """Close HTTP session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()