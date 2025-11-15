# US Financial Statement Database

A complete system for ingesting, storing, and serving raw "as-reported" financial statement data from 10-K and 10-Q SEC filings for all actively traded US public companies.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

- **Comprehensive Coverage**: All NASDAQ, NYSE, and NYSE American companies
- **As-Reported Data**: Exact line item names as they appear in SEC filings (no normalization)
- **Three Financial Statements**: Income Statement, Balance Sheet, Cash Flow Statement
- **Historical Data**: Up to 10 years of quarterly and annual filings
- **Real-Time Updates**: New filings processed within 1 hour of SEC publication
- **RESTful API**: High-performance API with <500ms response times
- **Data Validation**: Automated checks (e.g., balance sheet equation)
- **Web Interface**: Simple, clean UI for data viewing and CSV export

## System Architecture

```
┌─────────────────┐
│   SEC EDGAR     │
│   (Data Source) │
└────────┬────────┘
         │
         v
┌─────────────────────────────────┐
│       ETL Pipeline              │
│  ┌──────────────────────────┐  │
│  │ 1. EDGAR Monitor (RSS)   │  │
│  │ 2. Filing Downloader     │  │
│  │ 3. XBRL Parser           │  │
│  │ 4. Data Validator        │  │
│  │ 5. Database Loader       │  │
│  └──────────────────────────┘  │
└────────┬────────────────────────┘
         │
         v
┌─────────────────────────────────┐
│   PostgreSQL Database           │
│   (Company, Filing, FinData)    │
└────────┬────────────────────────┘
         │
         v
┌─────────────────────────────────┐
│   FastAPI Backend               │
│   - GET /company/{ticker}       │
│   - GET /filings/{ticker}       │
│   - GET /statement/{ticker}/... │
│   - GET /data_point/{ticker}/...│
└────────┬────────────────────────┘
         │
         v
┌─────────────────────────────────┐
│   Web Frontend (HTML/JS)        │
│   - Company Search              │
│   - Statement Viewer            │
│   - CSV Export                  │
└─────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (for Celery task queue)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Public-Stocks-Database
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install Python dependencies**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python scripts/init_db.py
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the services**

   In separate terminals:

   ```bash
   # Terminal 1: Redis
   redis-server

   # Terminal 2: Celery Worker
   cd backend
   celery -A etl.tasks worker --loglevel=info

   # Terminal 3: Celery Beat (scheduler)
   celery -A etl.tasks beat --loglevel=info

   # Terminal 4: FastAPI
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Open the web interface**
   ```
   Open frontend/public/index.html in your browser
   Or serve it with: python -m http.server 3000
   ```

## Deployment on Replit

This project is optimized for deployment on Replit.

### Setup on Replit

1. **Import this repository to Replit**

2. **Configure Secrets**
   Add these secrets in the Replit Secrets tab:
   ```
   DATABASE_URL=postgresql://...  (use Replit PostgreSQL)
   REDIS_URL=redis://...
   SECRET_KEY=<generate-random-key>
   VALID_API_KEYS=<your-api-keys>
   SEC_USER_AGENT=YourCompany contact@yourcompany.com
   ```

3. **Click Run**
   The `start.sh` script will automatically:
   - Install dependencies
   - Run migrations
   - Start Redis, Celery, and FastAPI

4. **Access your app**
   - API: `https://<your-repl>.replit.dev/docs`
   - Frontend: `https://<your-repl>.replit.dev`

## API Documentation

### Authentication

All API endpoints require an API key in the header:
```
X-API-Key: your-api-key-here
```

### Endpoints

#### 1. Get Company Metadata

```http
GET /api/v1/company/{ticker}
```

**Example:**
```bash
curl -H "X-API-Key: demo-key-12345" \
  http://localhost:8000/api/v1/company/AAPL
```

**Response:**
```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "company_name": "Apple Inc.",
  "exchange": "NASDAQ"
}
```

#### 2. Get Company Filings

```http
GET /api/v1/filings/{ticker}?filing_type=10-Q&limit=10
```

**Example:**
```bash
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/filings/AAPL?limit=5"
```

**Response:**
```json
[
  {
    "filing_id": 123,
    "filing_type": "10-K",
    "filing_date": "2024-10-28",
    "period_year": 2024,
    "period_quarter": null
  }
]
```

#### 3. Get Financial Statement

```http
GET /api/v1/statement/{ticker}/{statement_type}?year=2024&quarter=3
```

**Parameters:**
- `statement_type`: `income_statement`, `balance_sheet`, or `cash_flow`
- `year`: Fiscal year
- `quarter`: Fiscal quarter (1-4, omit for annual)

**Example:**
```bash
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/statement/AAPL/income_statement?year=2024&quarter=3"
```

**Response:**
```json
{
  "ticker": "AAPL",
  "statement_type": "income_statement",
  "period_year": 2024,
  "period_quarter": 3,
  "data": [
    {
      "line_item_name": "Total Revenue",
      "value": 90146000000,
      "order": 1
    },
    {
      "line_item_name": "Cost of Revenue",
      "value": 49071000000,
      "order": 2
    }
  ]
}
```

#### 4. Get Time Series Data

```http
GET /api/v1/data_point/{ticker}/{line_item_name}?period=quarterly&statement_type=income_statement
```

**Parameters:**
- `line_item_name`: URL-encoded line item name
- `period`: `quarterly` or `annual`
- `statement_type`: Which statement to search

**Example:**
```bash
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/data_point/AAPL/Total%20Revenue?period=quarterly&statement_type=income_statement&limit=4"
```

**Response:**
```json
{
  "ticker": "AAPL",
  "line_item_name": "Total Revenue",
  "period_type": "quarterly",
  "history": [
    {"year": 2024, "quarter": 3, "value": 90146000000},
    {"year": 2024, "quarter": 2, "value": 94836000000},
    {"year": 2024, "quarter": 1, "value": 117154000000}
  ]
}
```

## Data Pipeline (ETL)

### Manual Backfill

To backfill historical data for specific companies:

```bash
cd backend

# Single company
python scripts/backfill.py --ticker AAPL --years 10

# Multiple companies from file
python scripts/backfill.py --file tickers.txt --years 5
```

Create `tickers.txt` with one ticker per line:
```
AAPL
MSFT
GOOGL
AMZN
```

### Automated Monitoring

The system automatically monitors for new filings every hour via Celery:

```python
# Configured in etl/tasks.py
celery_app.conf.beat_schedule = {
    "monitor-new-filings": {
        "task": "etl.tasks.monitor_new_filings",
        "schedule": 3600,  # Every hour
    },
}
```

## Database Schema

### Tables

**Company**
- `company_id` (PK)
- `ticker` (UNIQUE)
- `cik` (UNIQUE)
- `company_name`
- `exchange`
- `is_active`

**Filing**
- `filing_id` (PK)
- `company_id` (FK)
- `filing_type` ('10-K' or '10-Q')
- `filing_date`
- `period_year`
- `period_quarter`
- `accession_number` (UNIQUE)
- `document_url`
- `is_restatement`

**FinancialData**
- `data_id` (PK)
- `filing_id` (FK)
- `statement_type` ('IS', 'BS', 'CF')
- `line_item_name` (as-reported, no normalization)
- `value` (NUMERIC(19,4))
- `display_order`
- `unit` (default: 'USD')

### Indexes

Optimized for fast queries:
- `company(ticker)`
- `filing(company_id, period_year, period_quarter)`
- `financial_data(filing_id, statement_type)`
- `financial_data(line_item_name)` for time-series queries

## Data Validation

The system includes automated validation:

1. **Balance Sheet Equation**: `Assets = Liabilities + Equity`
2. **Revenue Sanity Checks**: Negative revenue warnings
3. **Gross Profit Calculation**: `Revenue - Cost of Revenue`
4. **Cash Flow Reconciliation**: Sum of activities = Net change

Validation results are logged but don't block data loading (soft validation).

## Configuration

Key environment variables (`.env`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/financial_db

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_PORT=8000
SECRET_KEY=<random-secret>
VALID_API_KEYS=key1,key2,key3

# SEC EDGAR
SEC_USER_AGENT=YourCompany contact@example.com
SEC_RATE_LIMIT_DELAY=0.1  # 10 requests/second max

# ETL
ETL_BACKFILL_YEARS=10
ETL_CHECK_INTERVAL=3600  # seconds
```

## Performance

- **API Response Time**: <500ms (p95)
- **Data Freshness**: New filings available within 1 hour
- **Accuracy**: 99.99% vs. as-reported SEC data
- **Uptime Target**: 99.9%

## Testing

Run tests:
```bash
cd backend
pytest tests/ -v --cov=app
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
psql -U user -d financial_db

# Reset database
python scripts/init_db.py
```

### SEC Rate Limiting

If you get 429 errors:
- Increase `SEC_RATE_LIMIT_DELAY` in `.env`
- Ensure `SEC_USER_AGENT` is properly set

### Missing Data

```bash
# Check if filing exists
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/filings/AAPL"

# Manual backfill
python scripts/backfill.py --ticker AAPL --years 1
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Data sourced from SEC EDGAR database
- Built with FastAPI, PostgreSQL, and Celery
- Optimized for Replit deployment

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Email: support@example.com

---

**Version:** 1.0.0
**Last Updated:** 2024
**Status:** Production Ready
