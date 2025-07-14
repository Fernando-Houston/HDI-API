# HDI Project Research Summary & Implementation Plan

## Executive Summary

The HDI (Houston Data Intelligence) project aims to build a simple, focused live data platform leveraging Perplexity API for real-time Houston real estate intelligence. Based on comprehensive research, this document outlines the recommended tech stack, architecture, and implementation roadmap.

## Minimal Tech Stack Recommendations

### Core Technologies
1. **Backend API**: Flask 3.0+ with Flask-RESTX
2. **Frontend**: Streamlit 1.35+
3. **Caching**: Redis (via Flask-Caching)
4. **API Client**: OpenAI Python SDK (for Perplexity)
5. **Rate Limiting**: Flask-Limiter
6. **Documentation**: Flasgger (Swagger UI)
7. **Environment Management**: python-dotenv
8. **HTTP Client**: httpx (async support)
9. **Data Validation**: Pydantic
10. **Deployment**: Docker + Docker Compose

### Python Dependencies
```txt
flask==3.0.3
flask-restx==1.3.0
flask-caching==2.3.0
flask-limiter==3.7.0
flask-cors==4.0.1
flasgger==0.9.7
streamlit==1.35.0
openai==1.35.0
redis==5.0.6
pydantic==2.7.4
httpx==0.27.0
python-dotenv==1.0.1
gunicorn==22.0.0
```

## Project Structure

```
HDI/
├── backend/
│   ├── app.py                    # Flask application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── market.py         # Market endpoints
│   │   │   ├── neighborhoods.py  # Neighborhood endpoints
│   │   │   ├── properties.py     # Property endpoints
│   │   │   └── developments.py   # Development endpoints
│   │   └── middlewares/
│   │       ├── __init__.py
│   │       ├── rate_limiter.py   # Rate limiting logic
│   │       └── cache.py          # Caching middleware
│   ├── services/
│   │   ├── __init__.py
│   │   ├── perplexity_client.py # Perplexity API wrapper
│   │   └── data_formatter.py    # Response formatting
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic models
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # Configuration management
│   └── utils/
│       ├── __init__.py
│       └── exceptions.py         # Custom exceptions
├── frontend/
│   ├── streamlit_app.py          # Main Streamlit application
│   ├── pages/
│   │   ├── 1_Market_Trends.py
│   │   ├── 2_Neighborhoods.py
│   │   ├── 3_Properties.py
│   │   └── 4_Developments.py
│   └── components/
│       ├── __init__.py
│       ├── charts.py             # Visualization components
│       └── filters.py            # UI filter components
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── tests/
│   ├── test_api.py
│   ├── test_perplexity.py
│   └── test_cache.py
├── .env.example
├── requirements.txt
├── README.md
└── HDI_PROJECT_BLUEPRINT.md
```

## Architecture Design

### System Flow
```
User Query (Streamlit UI)
    ↓
Streamlit Frontend (Port 8501)
    ↓
Flask REST API (Port 5000)
    ↓ [Check Cache]
Redis Cache Layer
    ↓ [If cache miss]
Rate Limiter Check
    ↓
Perplexity API Client
    ↓
Response Formatting
    ↓
Cache Storage
    ↓
JSON Response to Streamlit
    ↓
Visualization & Display
```

## Key Implementation Patterns

### 1. Perplexity Integration Pattern
```python
class PerplexityClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("PERPLEXITY_API_KEY"),
            base_url="https://api.perplexity.ai"
        )
        
    async def query(self, prompt: str, model: str = "sonar-pro"):
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            return response
        except Exception as e:
            # Implement exponential backoff
            raise PerplexityAPIError(str(e))
```

### 2. Caching Strategy
- **5-minute cache**: Identical queries
- **30-minute cache**: Neighborhood-level data
- **24-hour cache**: Historical trend data
- **No cache**: Real-time property alerts

### 3. Rate Limiting Implementation
- **Per-user limits**: 20 req/min, 100 req/hour
- **Global limits**: 40 req/min to stay under Perplexity's 50 req/min
- **Endpoint-specific limits**: Higher for cached endpoints

## Identified Challenges & Solutions

### 1. Rate Limiting (Perplexity: 50 req/min)
**Solution**: Multi-tier caching + request queuing + user-level limits

### 2. Response Time Optimization
**Solution**: Redis caching + async processing + request batching

### 3. Error Handling for API Failures
**Solution**: Circuit breaker pattern + fallback responses + graceful degradation

### 4. Streamlit-Flask Communication
**Solution**: RESTful JSON API + session management + CORS configuration

## Step-by-Step Implementation Plan

### Phase 1: Foundation (Days 1-2)
1. Set up project structure and Git repository
2. Create virtual environment and install dependencies
3. Configure environment variables (.env file)
4. Set up Docker containers for Redis
5. Create basic Flask application with health check endpoint

### Phase 2: Perplexity Integration (Days 3-4)
1. Implement PerplexityClient wrapper class
2. Add error handling and retry logic
3. Create data formatting service
4. Test Perplexity API integration
5. Implement response caching logic

### Phase 3: API Development (Days 5-7)
1. Build Flask-RESTX API structure
2. Implement market trends endpoints
3. Add neighborhood analysis endpoints
4. Create property research endpoints
5. Build development tracking endpoints
6. Add Swagger documentation

### Phase 4: Middleware & Security (Days 8-9)
1. Implement Flask-Limiter rate limiting
2. Set up Flask-Caching with Redis
3. Add CORS configuration
4. Implement API key authentication (optional)
5. Add request/response logging

### Phase 5: Streamlit Frontend (Days 10-12)
1. Create main Streamlit application
2. Build search interface component
3. Implement visualization components
4. Create multi-page navigation
5. Add data export functionality
6. Implement error handling UI

### Phase 6: Integration & Testing (Days 13-14)
1. Connect Streamlit to Flask API
2. Test end-to-end data flow
3. Optimize caching strategies
4. Performance testing and optimization
5. Add unit and integration tests

### Phase 7: Deployment (Days 15-16)
1. Create Docker containers
2. Set up docker-compose configuration
3. Configure production environment
4. Deploy to cloud platform (AWS/GCP/Azure)
5. Set up monitoring and alerts

## Success Metrics

1. **Response Time**: < 5 seconds for 95% of requests
2. **Cache Hit Rate**: > 60% for common queries
3. **Uptime**: 99.9% availability
4. **Rate Limit Compliance**: Zero Perplexity API limit violations
5. **User Experience**: Intuitive UI with clear data visualizations

## Cost Projections

Based on Perplexity Sonar Pro pricing ($14/$10/$6 per 1000 requests):
- **Low Usage**: ~1000 requests/day = $6/day
- **Medium Usage**: ~5000 requests/day = $50/day
- **High Usage**: ~10000 requests/day = $140/day

With effective caching (60% hit rate), costs can be reduced by 60%.

## Next Steps

1. Review and approve tech stack recommendations
2. Set up development environment
3. Begin Phase 1 implementation
4. Schedule weekly progress reviews

## Recommendations

1. **Start Simple**: Focus on core functionality first
2. **Monitor Early**: Set up usage tracking from day one
3. **Cache Aggressively**: Maximize cache usage to reduce costs
4. **Document Everything**: Maintain clear API documentation
5. **Plan for Scale**: Design with future growth in mind

---

This research summary provides a clear path forward for building HDI as a focused, efficient live data platform while avoiding the over-engineering pitfalls of the previous system.