# HDI - Houston Data Intelligence Platform

A powerful real estate intelligence API for Houston, Texas. HDI combines multiple data sources including Perplexity AI and HCAD to provide comprehensive, real-time insights about the Houston real estate market.

## Features

- **Real-time Market Data**: Current prices, trends, and inventory
- **Property Intelligence**: Detailed property information from multiple sources
- **Investment Analysis**: ROI calculations and opportunity identification
- **Natural Language Queries**: Ask questions in plain English
- **Smart Caching**: Reduces costs and improves response times
- **Multi-source Fusion**: Combines AI insights with official records

## Quick Start

### 1. Set up environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Perplexity API key
```

### 3. Run the application

```bash
# Start Flask API
python -m backend.app

# API will be available at http://localhost:5000
# Swagger docs at http://localhost:5000/docs
```

### 4. Run the Streamlit Dashboard (Optional)

```bash
# Install frontend dependencies
pip install -r frontend/requirements.txt

# Start the dashboard
python frontend/run_dashboard.py

# Dashboard will be available at http://localhost:8501
```

**Dashboard Demo Mode:**
```bash
# Run demo with mock data (no API required)
streamlit run frontend/demo_app.py
```

### 5. Test the API

```bash
# Test Perplexity connection
python test_perplexity.py

# Check health endpoint
curl http://localhost:5000/health

# Try a market query
curl "http://localhost:5000/api/v1/market/trends?area=Houston%20Heights"
```

## API Endpoints

### Market Data
- `GET /api/v1/market/trends?area={area}` - Get current market trends
- `GET /api/v1/market/analysis?area={area}` - Get detailed analysis
- `GET /api/v1/market/forecast?area={area}` - Get market forecast

### Property Intelligence
- `POST /api/v1/properties/search` - Search with HCAD + market data fusion
- `GET /api/v1/properties/analyze?address={address}` - Analyze specific property
- `GET /api/v1/properties/hcad/{account}` - Direct HCAD lookup

### Natural Language Query
- `POST /api/v1/query` - Ask anything about Houston real estate

Example:
```json
{
  "query": "What are the best neighborhoods for investment under $500k?"
}
```

### Bulk Analysis (NEW!)
- `POST /api/v1/bulk/analyze` - Analyze up to 50 properties at once
- `GET /api/v1/bulk/compare?addresses={csv}` - Quick comparison of 2-5 properties
- `POST /api/v1/bulk/portfolio-analysis` - Portfolio-level investment analysis

### Analytics & Insights (NEW!)
- `GET /api/v1/analytics/stats/daily` - Daily usage statistics
- `GET /api/v1/analytics/stats/weekly` - Weekly breakdown
- `GET /api/v1/analytics/popular-queries` - Most popular searches
- `GET /api/v1/analytics/insights` - AI-generated insights
- `GET /api/v1/analytics/cost-breakdown` - Cost analysis by query type
- `GET /api/v1/analytics/performance-metrics` - System performance KPIs

### Smart Search & Opportunities (NEW!)
- `POST /api/v1/opportunities/find` - Find properties matching specific criteria
- `GET /api/v1/opportunities/quick-find` - Quick search with basic filters
- `POST /api/v1/opportunities/investment` - Investment-focused property search

### Houston Permits Integration (NEW!)
- `GET /api/v1/permits/by-address` - Get permits for specific property
- `GET /api/v1/permits/by-area` - Area-wide permit activity
- `GET /api/v1/permits/statistics` - Permit statistics and trends
- `GET /api/v1/permits/trends/{neighborhood}` - Neighborhood development trends
- `GET /api/v1/permits/property-intel` - Enhanced property intelligence with permits

### Automated Reports (NEW!)
- `POST /api/v1/reports/generate` - Generate a report on demand
- `GET /api/v1/reports/types` - Get available report types and descriptions
- `POST /api/v1/reports/preview` - Preview report sections before generation
- `POST /api/v1/reports/schedule` - Schedule recurring reports (placeholder)
- `GET /api/v1/reports/templates` - Get pre-configured report templates

## Streamlit Dashboard (NEW!)

HDI includes a comprehensive web dashboard for interactive data exploration:

### Features:
- **🔍 Property Search**: Natural language queries and address analysis
- **📊 Market Analysis**: Interactive charts and neighborhood trends
- **💰 Investment Opportunities**: AI-powered opportunity identification with filtering
- **🏗️ Building Permits**: Houston permit data with visualizations
- **📋 Automated Reports**: Generate and download comprehensive market reports
- **📈 Platform Analytics**: Usage tracking, cost monitoring, and performance metrics

### Pages:
- **Property Search & Analysis**: Search properties, analyze specific addresses, bulk compare
- **Market Analysis**: Area-specific market trends and insights
- **Investment Opportunities**: Find and score investment properties
- **Building Permits**: Track construction and renovation activity
- **Reports**: Generate automated market reports in multiple formats
- **Analytics**: Platform usage, costs, and performance monitoring

### Usage:
```bash
# Full dashboard (requires API)
python frontend/run_dashboard.py

# Demo mode (mock data, no API required)
streamlit run frontend/demo_app.py
```

## CLI Tool (NEW!)

HDI includes a powerful command-line interface for quick property searches:

```bash
# Install CLI
pip install -r requirements.txt

# Quick property search
./hdi_cli.py search "3bed 2bath under 400k in Heights"

# Analyze specific property
./hdi_cli.py analyze "1234 Main St, Houston, TX"

# Compare properties
./hdi_cli.py compare "1000 Main St" "2000 Bagby St" "3000 Post Oak"

# Get market trends
./hdi_cli.py market "Houston Heights"

# View usage stats
./hdi_cli.py stats

# Bulk analyze from file
./hdi_cli.py bulk addresses.txt --type investment

# Generate reports
./hdi_cli.py report daily_market "Heights,Montrose" --save
./hdi_cli.py report investment_opportunities "East End,Third Ward" --format markdown
./hdi_cli.py report-types
./hdi_cli.py report-templates
```

## Architecture

HDI uses a multi-tier architecture:

1. **API Layer**: Flask-RESTX with automatic documentation
2. **Business Logic**: Smart query routing and response enhancement
3. **Data Sources**: Perplexity AI (primary) + HCAD + fallback sources
4. **Caching**: Redis-based semantic caching
5. **Monitoring**: Built-in cost tracking and performance metrics
6. **Analytics**: Usage insights and optimization recommendations

## Development

### Project Structure
```
HDI/
├── backend/
│   ├── api/          # API endpoints
│   ├── services/     # Core services (Perplexity, HCAD)
│   ├── domain/       # Business logic
│   ├── config/       # Configuration
│   └── app.py       # Flask application
├── frontend/         # Streamlit UI (coming soon)
├── tests/           # Test suites
└── scripts/         # Utility scripts
```

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black backend/
flake8 backend/
```

## Deployment

HDI is designed for Railway deployment:

```bash
# Install Railway CLI
# railway login
# railway up
```

## Cost Optimization

HDI implements multiple strategies to minimize API costs:
- Semantic caching (not just exact matches)
- Query routing to optimal endpoints
- Fallback to free data sources
- Request batching and deduplication

Average cost per query: < $0.004 (vs $0.014 direct)

## Security

- Rate limiting per user and globally
- CORS configuration for web access
- API key authentication (optional)
- Request/response logging for audit

## Contributing

This is an internal project. For questions or issues, contact the development team.

## License

Proprietary - Internal Use Only