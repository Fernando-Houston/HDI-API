"""Bulk property analysis service for portfolio evaluation"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import structlog
from concurrent.futures import ThreadPoolExecutor
import json

from backend.services.data_fusion import DataFusionEngine
from backend.services.perplexity_client import PerplexityClient
from backend.utils.exceptions import HDIException

logger = structlog.get_logger(__name__)

class BulkAnalyzer:
    """Analyzes multiple properties efficiently"""
    
    def __init__(self, max_concurrent: int = 5):
        """
        Initialize bulk analyzer
        
        Args:
            max_concurrent: Maximum concurrent property analyses
        """
        self.max_concurrent = max_concurrent
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.fusion_engine = DataFusionEngine()
        logger.info("BulkAnalyzer initialized", max_concurrent=max_concurrent)
    
    async def analyze_properties(
        self,
        addresses: List[str],
        analysis_type: str = "standard",
        include_comparisons: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze multiple properties asynchronously
        
        Args:
            addresses: List of property addresses
            analysis_type: Type of analysis (standard, investment, quick)
            include_comparisons: Whether to include comparative analysis
            
        Returns:
            Comprehensive analysis results
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting bulk analysis for {len(addresses)} properties", analysis_type=analysis_type)
        
        # Validate inputs
        if not addresses:
            raise ValueError("No addresses provided")
        
        if len(addresses) > 50:
            raise ValueError("Maximum 50 properties per bulk analysis")
        
        # Analyze properties concurrently
        property_results = await self._analyze_properties_async(addresses, analysis_type)
        
        # Prepare response
        results = {
            "summary": self._generate_summary(property_results),
            "properties": property_results,
            "analysis_type": analysis_type,
            "total_properties": len(addresses),
            "successful_analyses": sum(1 for r in property_results if r.get("success", False)),
            "processing_time": (datetime.utcnow() - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add comparative analysis if requested
        if include_comparisons and len(property_results) > 1:
            results["comparison"] = self._compare_properties(property_results)
            results["rankings"] = self._rank_properties(property_results)
            results["opportunities"] = self._identify_opportunities(property_results)
        
        # Add market context
        results["market_context"] = await self._get_market_context(addresses)
        
        logger.info(
            "Bulk analysis completed",
            total=len(addresses),
            successful=results["successful_analyses"],
            time=results["processing_time"]
        )
        
        return results
    
    async def _analyze_properties_async(
        self,
        addresses: List[str],
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """Analyze properties concurrently"""
        # Create tasks for concurrent execution
        tasks = []
        
        for address in addresses:
            if analysis_type == "quick":
                task = self._quick_analysis(address)
            elif analysis_type == "investment":
                task = self._investment_analysis(address)
            else:
                task = self._standard_analysis(address)
            
            tasks.append(task)
        
        # Execute with rate limiting
        results = []
        for i in range(0, len(tasks), self.max_concurrent):
            batch = tasks[i:i + self.max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
            
            # Small delay between batches to avoid rate limits
            if i + self.max_concurrent < len(tasks):
                await asyncio.sleep(1)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Analysis failed for {addresses[i]}", error=str(result))
                processed_results.append({
                    "address": addresses[i],
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _standard_analysis(self, address: str) -> Dict[str, Any]:
        """Standard property analysis"""
        loop = asyncio.get_event_loop()
        
        try:
            # Run synchronous fusion engine in executor
            result = await loop.run_in_executor(
                self.executor,
                self.fusion_engine.get_property_intelligence,
                address
            )
            
            return {
                "address": address,
                "success": True,
                "data": result,
                "analysis_type": "standard"
            }
        except Exception as e:
            logger.error(f"Standard analysis failed for {address}", error=str(e))
            return {
                "address": address,
                "success": False,
                "error": str(e)
            }
    
    async def _quick_analysis(self, address: str) -> Dict[str, Any]:
        """Quick analysis with basic data only"""
        loop = asyncio.get_event_loop()
        
        try:
            # Just get HCAD data for quick analysis
            result = await loop.run_in_executor(
                self.executor,
                self.fusion_engine.hcad.get_property_by_address,
                address
            )
            
            return {
                "address": address,
                "success": True,
                "data": {
                    "official_data": result,
                    "quick_insights": self._generate_quick_insights(result)
                },
                "analysis_type": "quick"
            }
        except Exception as e:
            logger.error(f"Quick analysis failed for {address}", error=str(e))
            return {
                "address": address,
                "success": False,
                "error": str(e)
            }
    
    async def _investment_analysis(self, address: str) -> Dict[str, Any]:
        """Detailed investment analysis"""
        # Get standard analysis first
        standard = await self._standard_analysis(address)
        
        if not standard.get("success"):
            return standard
        
        # Enhance with investment metrics
        loop = asyncio.get_event_loop()
        
        try:
            # Get investment-specific insights
            investment_prompt = f"""
            Analyze investment potential for {address}, Houston, TX:
            - Estimated rental income
            - Cap rate
            - Cash flow potential
            - Appreciation forecast
            - Investment risks
            - ROI projections
            """
            
            client = PerplexityClient()
            investment_data = await loop.run_in_executor(
                self.executor,
                client.query,
                investment_prompt
            )
            
            # Combine results
            standard["data"]["investment_analysis"] = investment_data.get("data")
            standard["analysis_type"] = "investment"
            
            # Calculate investment score
            standard["data"]["investment_score"] = self._calculate_investment_score(standard["data"])
            
            return standard
            
        except Exception as e:
            logger.error(f"Investment analysis failed for {address}", error=str(e))
            standard["investment_error"] = str(e)
            return standard
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate executive summary of all properties"""
        successful = [r for r in results if r.get("success", False)]
        
        if not successful:
            return {"error": "No successful analyses"}
        
        summary = {
            "total_analyzed": len(successful),
            "average_confidence": sum(
                r.get("data", {}).get("confidence_score", 0) 
                for r in successful
            ) / len(successful),
            "properties_with_hcad_data": sum(
                1 for r in successful 
                if r.get("data", {}).get("official_data")
            ),
            "properties_with_market_data": sum(
                1 for r in successful 
                if r.get("data", {}).get("market_insights")
            )
        }
        
        # Extract value statistics if available
        values = []
        for r in successful:
            if r.get("data", {}).get("official_data", {}).get("appraised_value"):
                try:
                    value = float(str(r["data"]["official_data"]["appraised_value"]).replace("$", "").replace(",", ""))
                    values.append(value)
                except:
                    pass
        
        if values:
            summary["value_statistics"] = {
                "total_value": sum(values),
                "average_value": sum(values) / len(values),
                "min_value": min(values),
                "max_value": max(values)
            }
        
        return summary
    
    def _compare_properties(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare properties against each other"""
        successful = [r for r in results if r.get("success", False)]
        
        if len(successful) < 2:
            return {"error": "Need at least 2 successful analyses to compare"}
        
        comparison = {
            "property_count": len(successful),
            "comparison_matrix": [],
            "key_differences": []
        }
        
        # Create comparison matrix
        for i, prop1 in enumerate(successful):
            for j, prop2 in enumerate(successful):
                if i < j:  # Avoid duplicate comparisons
                    comparison["comparison_matrix"].append({
                        "property1": prop1["address"],
                        "property2": prop2["address"],
                        "value_difference": self._calculate_value_difference(prop1, prop2),
                        "confidence_difference": abs(
                            prop1.get("data", {}).get("confidence_score", 0) -
                            prop2.get("data", {}).get("confidence_score", 0)
                        )
                    })
        
        return comparison
    
    def _rank_properties(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank properties by various criteria"""
        successful = [r for r in results if r.get("success", False)]
        
        rankings = []
        
        # Rank by investment score if available
        investment_scores = []
        for r in successful:
            score = r.get("data", {}).get("investment_score", 0)
            if score:
                investment_scores.append({
                    "address": r["address"],
                    "score": score,
                    "data": r["data"]
                })
        
        if investment_scores:
            investment_scores.sort(key=lambda x: x["score"], reverse=True)
            rankings.append({
                "criteria": "investment_potential",
                "ranked_properties": [
                    {"rank": i+1, "address": p["address"], "score": p["score"]}
                    for i, p in enumerate(investment_scores)
                ]
            })
        
        # Rank by value if available
        value_rankings = []
        for r in successful:
            value = self._extract_property_value(r)
            if value:
                value_rankings.append({
                    "address": r["address"],
                    "value": value
                })
        
        if value_rankings:
            value_rankings.sort(key=lambda x: x["value"])
            rankings.append({
                "criteria": "lowest_value",
                "ranked_properties": [
                    {"rank": i+1, "address": p["address"], "value": f"${p['value']:,.0f}"}
                    for i, p in enumerate(value_rankings)
                ]
            })
        
        return rankings
    
    def _identify_opportunities(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify investment opportunities from bulk analysis"""
        opportunities = []
        
        for r in results:
            if not r.get("success"):
                continue
            
            # Check for undervalued properties
            market_insights = r.get("data", {}).get("market_insights", "")
            if "below market" in market_insights.lower() or "undervalued" in market_insights.lower():
                opportunities.append({
                    "type": "undervalued",
                    "address": r["address"],
                    "reason": "Property appears to be priced below market value",
                    "confidence": r.get("data", {}).get("confidence_score", 0)
                })
            
            # Check for high investment score
            investment_score = r.get("data", {}).get("investment_score", 0)
            if investment_score > 7:  # Threshold for good investment
                opportunities.append({
                    "type": "high_roi_potential",
                    "address": r["address"],
                    "reason": f"High investment score: {investment_score}/10",
                    "confidence": r.get("data", {}).get("confidence_score", 0)
                })
        
        return opportunities
    
    async def _get_market_context(self, addresses: List[str]) -> Dict[str, Any]:
        """Get overall market context for the properties"""
        # Extract neighborhoods from addresses
        neighborhoods = set()
        for address in addresses:
            # Simple extraction - could be improved
            parts = address.split(",")
            if len(parts) > 1:
                potential_neighborhood = parts[0].split()[-1]  # Last word before comma
                neighborhoods.add(potential_neighborhood)
        
        if not neighborhoods:
            return {"error": "Could not determine neighborhoods"}
        
        # Get market data for neighborhoods
        loop = asyncio.get_event_loop()
        client = PerplexityClient()
        
        market_prompt = f"""
        Provide brief market context for these Houston neighborhoods: {', '.join(neighborhoods)}
        Include: current trends, average prices, market direction
        """
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                client.query,
                market_prompt
            )
            
            return {
                "neighborhoods": list(neighborhoods),
                "market_summary": result.get("data", "No market data available")
            }
        except Exception as e:
            logger.error("Failed to get market context", error=str(e))
            return {"error": str(e)}
    
    def _generate_quick_insights(self, hcad_data: Optional[Dict]) -> List[str]:
        """Generate quick insights from HCAD data"""
        insights = []
        
        if not hcad_data:
            return ["No HCAD data available"]
        
        # Extract key metrics
        if "values" in hcad_data:
            total_value = hcad_data["values"].get("Total", 0)
            if total_value:
                insights.append(f"Appraised value: ${total_value:,.0f}")
        
        if "property_info" in hcad_data:
            year_built = hcad_data["property_info"].get("year_built")
            if year_built:
                age = datetime.now().year - int(year_built)
                insights.append(f"Property age: {age} years")
        
        return insights
    
    def _calculate_investment_score(self, property_data: Dict[str, Any]) -> float:
        """Calculate investment score (0-10)"""
        score = 5.0  # Base score
        
        # Adjust based on confidence
        confidence = property_data.get("confidence_score", 0.5)
        score += (confidence - 0.5) * 2
        
        # Adjust based on market insights
        insights = str(property_data.get("market_insights", "")).lower()
        if "high demand" in insights or "appreciating" in insights:
            score += 1
        if "declining" in insights or "oversupply" in insights:
            score -= 1
        
        # Ensure score is between 0 and 10
        return max(0, min(10, score))
    
    def _calculate_value_difference(self, prop1: Dict, prop2: Dict) -> Optional[float]:
        """Calculate value difference between properties"""
        value1 = self._extract_property_value(prop1)
        value2 = self._extract_property_value(prop2)
        
        if value1 and value2:
            return abs(value1 - value2)
        
        return None
    
    def _extract_property_value(self, property_result: Dict) -> Optional[float]:
        """Extract numeric value from property result"""
        try:
            value_str = property_result.get("data", {}).get("official_data", {}).get("appraised_value", "")
            if value_str:
                return float(str(value_str).replace("$", "").replace(",", ""))
        except:
            pass
        
        return None