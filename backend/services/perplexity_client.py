"""Perplexity API client for real-time Houston data"""

import asyncio
from typing import Optional, Dict, Any, List
import httpx
from openai import OpenAI
import structlog
from datetime import datetime
import time

from backend.config.settings import settings
from backend.utils.exceptions import PerplexityAPIError, RateLimitError
from backend.utils.cache import cached_perplexity

logger = structlog.get_logger(__name__)

class PerplexityClient:
    """Client for interacting with Perplexity API"""
    
    def __init__(self):
        """Initialize Perplexity client with OpenAI SDK"""
        self.client = OpenAI(
            api_key=settings.PERPLEXITY_API_KEY,
            base_url=settings.PERPLEXITY_BASE_URL
        )
        self.model = settings.PERPLEXITY_MODEL  # "sonar" not "sonar-pro"
        self.request_count = 0
        self.total_cost = 0.0
        logger.info("PerplexityClient initialized", model=self.model)
    
    @cached_perplexity(ttl_seconds=86400)  # Cache for 24 hours
    def query(self, prompt: str, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Make a synchronous query to Perplexity API
        
        Args:
            prompt: The query prompt
            temperature: Response randomness (0.0-1.0)
            
        Returns:
            Dict containing response and metadata
        """
        start_time = time.time()
        
        try:
            logger.info("Sending query to Perplexity", model=self.model)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Houston real estate expert. Provide accurate, current data with sources."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                stream=False
            )
            
            # Extract response
            content = response.choices[0].message.content
            
            # Calculate cost
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            query_cost = self._calculate_cost(tokens_used)
            
            # Update tracking
            self.request_count += 1
            self.total_cost += query_cost
            
            # Prepare response
            result = {
                "data": content,
                "metadata": {
                    "model": self.model,
                    "tokens_used": tokens_used,
                    "cost": query_cost,
                    "response_time": time.time() - start_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_count": self.request_count
                },
                "success": True
            }
            
            logger.info(
                "Perplexity query successful",
                cost=query_cost,
                tokens=tokens_used,
                response_time=result["metadata"]["response_time"]
            )
            
            return result
            
        except Exception as e:
            logger.error("Perplexity query failed", error=str(e), model=self.model)
            
            if "rate_limit" in str(e).lower():
                raise RateLimitError(f"Perplexity rate limit exceeded: {str(e)}")
            
            raise PerplexityAPIError(f"Perplexity API error: {str(e)}")
    
    async def query_async(self, prompt: str, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Make an asynchronous query to Perplexity API
        
        Args:
            prompt: The query prompt
            temperature: Response randomness (0.0-1.0)
            
        Returns:
            Dict containing response and metadata
        """
        # Run sync method in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.query, prompt, temperature)
    
    def query_with_template(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """
        Query using a predefined template
        
        Args:
            template_name: Name of the query template
            **kwargs: Template parameters
            
        Returns:
            Query response
        """
        from backend.services.query_templates import QUERY_TEMPLATES
        
        if template_name not in QUERY_TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = QUERY_TEMPLATES[template_name]
        prompt = template.format(**kwargs)
        
        return self.query(prompt)
    
    def batch_query(self, prompts: List[str]) -> List[Dict[str, Any]]:
        """
        Execute multiple queries (with rate limiting)
        
        Args:
            prompts: List of query prompts
            
        Returns:
            List of query responses
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            try:
                result = self.query(prompt)
                results.append(result)
                
                # Rate limiting: wait between requests
                if i < len(prompts) - 1:
                    time.sleep(1.2)  # ~50 requests per minute limit
                    
            except Exception as e:
                logger.error(f"Batch query {i} failed", error=str(e))
                results.append({
                    "data": None,
                    "error": str(e),
                    "success": False
                })
        
        return results
    
    def _calculate_cost(self, tokens: int) -> float:
        """
        Calculate query cost based on tokens used
        
        Args:
            tokens: Number of tokens used
            
        Returns:
            Cost in dollars
        """
        # Using low tier pricing: $6 per 1000 requests
        # Approximate cost per token (assuming ~1000 tokens per request average)
        cost_per_1000_requests = settings.PERPLEXITY_COST_PER_1000
        estimated_cost = (cost_per_1000_requests / 1000)  # Cost per request
        
        return estimated_cost
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get client usage statistics"""
        return {
            "total_requests": self.request_count,
            "total_cost": round(self.total_cost, 4),
            "average_cost_per_request": round(
                self.total_cost / self.request_count if self.request_count > 0 else 0,
                4
            ),
            "model": self.model
        }
    
    def health_check(self) -> bool:
        """Check if Perplexity API is accessible"""
        try:
            # Simple test query
            response = self.query("What is 2+2?", temperature=0)
            return response.get("success", False)
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False