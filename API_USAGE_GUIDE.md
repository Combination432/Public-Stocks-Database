# API Usage Guide

Quick reference for using the US Financial Statement Database API.

## Authentication

All API requests require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/api/v1/company/AAPL
```

## Base URL

- Local: `http://localhost:8000/api/v1`
- Replit: `https://<your-repl>.replit.dev/api/v1`

## Quick Examples

### 1. Get Company Information

```bash
curl -H "X-API-Key: demo-key-12345" \
  http://localhost:8000/api/v1/company/AAPL
```

### 2. List All Filings

```bash
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/filings/AAPL?limit=10"
```

### 3. Get Latest Quarterly Income Statement

```bash
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/statement/AAPL/income_statement?year=2024&quarter=3"
```

### 4. Get Annual Balance Sheet

```bash
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/statement/AAPL/balance_sheet?year=2024"
```

### 5. Get Revenue Time Series

```bash
curl -H "X-API-Key: demo-key-12345" \
  "http://localhost:8000/api/v1/data_point/AAPL/Total%20Revenue?period=quarterly&limit=8"
```

## Python Client

```python
import requests

class FinancialAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}

    def get_company(self, ticker):
        url = f"{self.base_url}/company/{ticker}"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_statement(self, ticker, statement_type, year, quarter=None):
        url = f"{self.base_url}/statement/{ticker}/{statement_type}"
        params = {"year": year}
        if quarter:
            params["quarter"] = quarter
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

# Usage
api = FinancialAPI("http://localhost:8000/api/v1", "demo-key-12345")
company = api.get_company("AAPL")
statement = api.get_statement("AAPL", "income_statement", 2024, 3)
```

## JavaScript Client

```javascript
class FinancialAPI {
    constructor(baseURL, apiKey) {
        this.baseURL = baseURL;
        this.apiKey = apiKey;
    }

    async getCompany(ticker) {
        const response = await fetch(`${this.baseURL}/company/${ticker}`, {
            headers: { 'X-API-Key': this.apiKey }
        });
        return response.json();
    }

    async getStatement(ticker, statementType, year, quarter = null) {
        let url = `${this.baseURL}/statement/${ticker}/${statementType}?year=${year}`;
        if (quarter) url += `&quarter=${quarter}`;

        const response = await fetch(url, {
            headers: { 'X-API-Key': this.apiKey }
        });
        return response.json();
    }
}

// Usage
const api = new FinancialAPI('http://localhost:8000/api/v1', 'demo-key-12345');
const company = await api.getCompany('AAPL');
const statement = await api.getStatement('AAPL', 'income_statement', 2024, 3);
```

## Common Use Cases

### Compare Revenue Across Companies

```python
companies = ['AAPL', 'MSFT', 'GOOGL']
year = 2024
quarter = 3

for ticker in companies:
    data = api.get_statement(ticker, 'income_statement', year, quarter)
    revenue = next(
        (item['value'] for item in data['data']
         if 'Revenue' in item['line_item_name']),
        None
    )
    print(f"{ticker}: ${revenue:,.0f}")
```

### Track Metric Over Time

```python
ticker = 'AAPL'
metric = 'Total Revenue'

response = api.get_data_point(ticker, metric, period='quarterly', limit=8)

for point in response['history']:
    period = f"Q{point['quarter']} {point['year']}"
    value = f"${point['value']:,.0f}"
    print(f"{period}: {value}")
```

### Build Financial Ratios

```python
def get_line_item(data, keyword):
    """Find line item by keyword"""
    for item in data['data']:
        if keyword.lower() in item['line_item_name'].lower():
            return item['value']
    return None

# Get balance sheet
bs = api.get_statement('AAPL', 'balance_sheet', 2024, 3)

assets = get_line_item(bs, 'total assets')
liabilities = get_line_item(bs, 'total liabilities')

if assets and liabilities:
    debt_to_assets = liabilities / assets
    print(f"Debt-to-Assets Ratio: {debt_to_assets:.2%}")
```

## Response Formats

### Company Response
```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "company_name": "Apple Inc.",
  "exchange": "NASDAQ"
}
```

### Statement Response
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
    }
  ]
}
```

### Time Series Response
```json
{
  "ticker": "AAPL",
  "line_item_name": "Total Revenue",
  "period_type": "quarterly",
  "history": [
    {
      "year": 2024,
      "quarter": 3,
      "value": 90146000000
    }
  ]
}
```

## Error Handling

```python
import requests

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise exception for 4xx/5xx
    data = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Resource not found")
    elif e.response.status_code == 401:
        print("Invalid API key")
    else:
        print(f"HTTP error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

## Rate Limiting

- Free tier: 100 requests/hour
- Pro tier: 1000 requests/hour

Headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

## Best Practices

1. **Cache responses** - Financial data doesn't change frequently
2. **Batch requests** - Use time series endpoint instead of multiple individual requests
3. **Handle errors gracefully** - Always check response status
4. **Respect rate limits** - Implement exponential backoff
5. **Use appropriate periods** - Quarterly for trends, annual for comparisons

## Interactive API Documentation

Visit `/docs` for interactive Swagger UI:
- http://localhost:8000/docs
- https://<your-repl>.replit.dev/docs

## Support

- GitHub Issues: [repository-url]/issues
- Email: support@example.com
- Documentation: See README.md
