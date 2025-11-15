"""
Data point endpoints.

GET /data_point/{ticker}/{line_item_name} - Get time series for a specific line item
"""
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_db, require_api_key
from app.crud.company import company_crud
from app.crud.financial_data import financial_data_crud
from app.schemas.financial_data import TimeSeriesDataPoint, TimeSeriesResponse

router = APIRouter()

# Map user-friendly names to database codes
STATEMENT_TYPE_MAP = {
    "income_statement": "IS",
    "balance_sheet": "BS",
    "cash_flow": "CF",
}


@router.get("/{ticker}/{line_item_name:path}", response_model=TimeSeriesResponse)
async def get_data_point_time_series(
    ticker: str = Path(..., description="Stock ticker symbol"),
    line_item_name: str = Path(..., description="Line item name (URL-encoded if contains special chars)"),
    period: str = Query(
        "quarterly",
        regex="^(quarterly|annual)$",
        description="Period type: 'quarterly' or 'annual'",
    ),
    statement_type: str = Query(
        "income_statement",
        regex="^(income_statement|balance_sheet|cash_flow)$",
        description="Statement type to search in",
    ),
    limit: int = Query(40, ge=1, le=200, description="Maximum number of periods to return"),
    db: AsyncSession = Depends(get_current_db),
    api_key: str = Depends(require_api_key),
) -> TimeSeriesResponse:
    """
    Get time series data for a specific line item.

    **Parameters:**
    - **ticker**: Stock ticker symbol (e.g., AAPL)
    - **line_item_name**: Exact as-reported line item name (URL-encoded)
      - Example: `Total Revenue`, `Net Income`, `Total Assets`
    - **period**: Period type
      - `quarterly` - Quarterly data (10-Q filings)
      - `annual` - Annual data (10-K filings)
    - **statement_type**: Which statement to search in
      - `income_statement`, `balance_sheet`, or `cash_flow`
    - **limit**: Maximum number of periods (default: 40, max: 200)

    **Returns:**
    - Time series of the line item ordered by period (most recent first)

    **Example Response:**
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
            },
            {
                "year": 2024,
                "quarter": 2,
                "value": 94836000000
            },
            {
                "year": 2024,
                "quarter": 1,
                "value": 117154000000
            }
        ]
    }
    ```
    """
    # URL decode the line item name
    line_item_name = unquote(line_item_name)

    # Get company
    company = await company_crud.get_by_ticker(db, ticker.upper())
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{ticker}' not found",
        )

    # Map statement type
    db_statement_type = STATEMENT_TYPE_MAP[statement_type]

    # Get time series data
    history = await financial_data_crud.get_line_item_history(
        db,
        company.company_id,
        line_item_name,
        db_statement_type,
        period,
        limit,
    )

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for line item '{line_item_name}' in {statement_type}",
        )

    # Convert to response format
    data_points = [
        TimeSeriesDataPoint(
            year=filing.period_year,
            quarter=filing.period_quarter,
            value=float(data.value) if data.value is not None else None,
        )
        for filing, data in history
    ]

    return TimeSeriesResponse(
        ticker=ticker.upper(),
        line_item_name=line_item_name,
        period_type=period,
        history=data_points,
    )
