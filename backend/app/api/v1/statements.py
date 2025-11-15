"""
Statement endpoints.

GET /statement/{ticker}/{statement_type} - Get full financial statement
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_db, require_api_key
from app.crud.company import company_crud
from app.crud.filing import filing_crud
from app.crud.financial_data import financial_data_crud
from app.schemas.financial_data import LineItem, StatementResponse

router = APIRouter()

# Map user-friendly names to database codes
STATEMENT_TYPE_MAP = {
    "income_statement": "IS",
    "balance_sheet": "BS",
    "cash_flow": "CF",
}


@router.get("/{ticker}/{statement_type}", response_model=StatementResponse)
async def get_statement(
    ticker: str = Path(..., description="Stock ticker symbol"),
    statement_type: str = Path(
        ...,
        regex="^(income_statement|balance_sheet|cash_flow)$",
        description="Statement type: income_statement, balance_sheet, or cash_flow",
    ),
    year: int = Query(..., ge=1990, le=2100, description="Fiscal year"),
    quarter: int | None = Query(None, ge=1, le=4, description="Fiscal quarter (1-4, omit for annual)"),
    db: AsyncSession = Depends(get_current_db),
    api_key: str = Depends(require_api_key),
) -> StatementResponse:
    """
    Get a full financial statement for a specific period.

    **Parameters:**
    - **ticker**: Stock ticker symbol (e.g., AAPL)
    - **statement_type**: Type of statement
      - `income_statement` - Income Statement (IS)
      - `balance_sheet` - Balance Sheet (BS)
      - `cash_flow` - Cash Flow Statement (CF)
    - **year**: Fiscal year (e.g., 2024)
    - **quarter**: Fiscal quarter (1-4). Omit for annual (10-K) data.

    **Returns:**
    - Financial statement with all line items in display order

    **Example Response:**
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
    """
    # Get company
    company = await company_crud.get_by_ticker(db, ticker.upper())
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{ticker}' not found",
        )

    # Get filing for the period
    filing = await filing_crud.get_filing_for_period(db, company.company_id, year, quarter)
    if not filing:
        period_desc = f"Q{quarter} {year}" if quarter else f"FY {year}"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No filing found for {ticker} for period {period_desc}",
        )

    # Map statement type
    db_statement_type = STATEMENT_TYPE_MAP[statement_type]

    # Get financial data
    financial_data = await financial_data_crud.get_statement_data(
        db, filing.filing_id, db_statement_type
    )

    if not financial_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {statement_type} data found for this filing",
        )

    # Convert to response format
    line_items = [
        LineItem(
            line_item_name=item.line_item_name,
            value=float(item.value) if item.value is not None else None,
            display_order=item.display_order,
        )
        for item in financial_data
    ]

    return StatementResponse(
        ticker=ticker.upper(),
        statement_type=statement_type,
        period_year=year,
        period_quarter=quarter,
        data=line_items,
    )
