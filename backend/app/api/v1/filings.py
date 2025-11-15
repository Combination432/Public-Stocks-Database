"""
Filings endpoints.

GET /filings/{ticker} - Get list of filings for a company
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_db, require_api_key
from app.crud.company import company_crud
from app.crud.filing import filing_crud
from app.schemas.filing import FilingResponse

router = APIRouter()


@router.get("/{ticker}", response_model=List[FilingResponse])
async def get_company_filings(
    ticker: str,
    filing_type: str | None = Query(None, regex="^(10-K|10-Q)$"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_current_db),
    api_key: str = Depends(require_api_key),
) -> List[FilingResponse]:
    """
    Get all filings for a company.

    **Parameters:**
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)
    - **filing_type**: Optional filter by filing type (10-K or 10-Q)
    - **limit**: Maximum number of filings to return (default: 100, max: 500)

    **Returns:**
    - List of filings ordered by filing date (most recent first)

    **Example Response:**
    ```json
    [
        {
            "filing_id": 123,
            "filing_type": "10-K",
            "filing_date": "2024-10-28",
            "period_year": 2024,
            "period_quarter": null
        },
        {
            "filing_id": 124,
            "filing_type": "10-Q",
            "filing_date": "2024-07-25",
            "period_year": 2024,
            "period_quarter": 3
        }
    ]
    ```
    """
    # Get company
    company = await company_crud.get_by_ticker(db, ticker.upper())
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{ticker}' not found",
        )

    # Get filings
    filings = await filing_crud.get_company_filings(
        db, company.company_id, filing_type, limit
    )

    return [
        FilingResponse(
            filing_id=f.filing_id,
            filing_type=f.filing_type,
            filing_date=f.filing_date,
            period_year=f.period_year,
            period_quarter=f.period_quarter,
        )
        for f in filings
    ]
