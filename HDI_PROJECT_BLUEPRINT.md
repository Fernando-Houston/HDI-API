# HDI - Houston Data Intelligence (Live Data Platform)

## Project Overview
**HDI = Houston Data Intelligence**  
**Purpose**: Real-time Houston real estate data platform using Perplexity API

## What HDI Is
- **Live Data Platform**: Real-time Houston market intelligence
- **Research Tool**: Current market trends, prices, developments
- **Data API**: Clean endpoints for accessing Houston real estate data
- **NOT**: Content generation (that's a separate project)

## Core Components
1. **Perplexity Integration** - Live Houston data source
2. **API Endpoints** - RESTful data access
3. **Streamlit UI** - Interactive data exploration

## Architecture (Simple & Focused)
```
User Query → Streamlit UI → Flask API → Perplexity API
                                ↓
                          Response Cache
                                ↓
                          Formatted Data
```

## Key Features for HDI

### 1. Live Market Data
```python
GET /api/market/trends?area=Houston Heights
Response: Current prices, inventory, trends
```

### 2. Development Intelligence
```python
GET /api/developments/active?area=River Oaks
Response: Current projects, permits, timelines
```

### 3. Neighborhood Analysis
```python
GET /api/neighborhoods/{name}/analysis
Response: Demographics, growth, investment potential
```

### 4. Property Research
```python
POST /api/property/research
{
  "address": "1000 Main St, Houston, TX"
}
Response: Property details, history, comparables
```

### 5. Investment Opportunities
```python
POST /api/opportunities/find
{
  "budget": "500000-1000000",
  "type": "residential",
  "criteria": ["high-growth", "good-schools"]
}
```

## How HDI Will Be Used

### Primary Use Cases
1. **Market Research**: "What's happening in Houston Heights right now?"
2. **Investment Analysis**: "Find growing neighborhoods under $400k median"
3. **Development Tracking**: "New projects in Medical Center area"
4. **Competitive Intelligence**: "Top developers by permit volume"
5. **Risk Assessment**: "Flood risk analysis for specific areas"

### Users
- Real estate investors
- Developers
- Internal research team
- Content team (will use HDI data for SEO project)

## Technical Implementation

### API Structure
```python
/api/v1/
  /market
    /trends
    /analysis
    /forecast
  /neighborhoods
    /{name}
    /compare
    /rankings
  /properties
    /search
    /analyze
    /history
  /developments
    /active
    /planned
    /completed
  /opportunities
    /investment
    /development
    /distressed
```

### Streamlit UI Components
1. **Search Bar**: Natural language queries
2. **Dashboard**: Key market metrics
3. **Maps**: Visual property/area data
4. **Reports**: Downloadable analysis
5. **Alerts**: Market change notifications

### Data Response Format
```json
{
  "status": "success",
  "data": {
    "summary": "Human-readable summary",
    "metrics": {
      "median_price": 450000,
      "inventory_months": 2.3,
      "price_change_yoy": 5.2
    },
    "insights": ["Key finding 1", "Key finding 2"],
    "sources": ["Source 1", "Source 2"],
    "timestamp": "2025-07-12T10:30:00Z"
  }
}
```

## What HDI is NOT
- ❌ Content generator
- ❌ SEO tool
- ❌ Static report processor
- ❌ Complex multi-agent system

## Success Metrics
- Real-time data (< 5 second responses)
- Accurate, sourced information
- Easy-to-use interface
- Reliable API for other projects

## Environment Setup
```bash
# Required
PERPLEXITY_API_KEY=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

# Optional
CACHE_TIMEOUT=300  # 5 minutes
RATE_LIMIT=100    # requests per hour
```

## Simple File Structure
```
HDI/
├── app.py                 # Flask API
├── perplexity_client.py   # Perplexity wrapper
├── data_formatter.py      # Format responses
├── cache_manager.py       # Simple caching
├── streamlit_app.py       # UI
├── requirements.txt
└── README.md
```

## Integration with Other Projects
HDI will serve as the **data backbone** for:
1. **SEO Content Project**: Pull live data for content generation
2. **Website Updates**: Real-time market stats
3. **Email Reports**: Weekly market summaries
4. **Internal Dashboards**: Team research

## Key Design Principles
1. **Real-time First**: Always prefer live data
2. **Simple Queries**: Natural language → data
3. **Clean Responses**: Structured, consistent JSON
4. **Fast**: Cache smartly, fail gracefully
5. **Reliable**: No complex dependencies

## Example Usage Flow
```
User: "What's the current market in Houston Heights?"
         ↓
Streamlit: Sends to API
         ↓
API: Checks cache (5 min TTL)
         ↓
Perplexity: "Houston Heights real estate market analysis 2025"
         ↓
API: Formats response with metrics, insights, sources
         ↓
Streamlit: Displays charts, metrics, summary
         ↓
User: Gets real-time intelligence
```

---
**HDI = Houston Data Intelligence**  
**Purpose**: Live data platform (not content generation)  
**Next Step**: Build clean, focused implementation