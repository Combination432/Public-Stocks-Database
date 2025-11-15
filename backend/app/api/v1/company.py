"""
Company endpoints.

GET /company/{ticker} - Get company metadata
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_db, require_api_key
from app.crud.company import company_crud
from app.schemas.company import CompanyResponse

router = APIRouter()


@router.get("/{ticker}", response_model=CompanyResponse)
async def get_company(
    ticker: str,
    db: AsyncSession = Depends(get_current_db),
    api_key: str = Depends(require_api_key),
) -> CompanyResponse:
    """
    Get company metadata by ticker symbol.

    **Parameters:**
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)

    **Returns:**
    - Company metadata including ticker, CIK, name, and exchange

    **Example Response:**
    ```json
    {
        "ticker": "AAPL",
        "cik": "0000320193",
        "company_name": "Apple Inc.",
        "exchange": "NASDAQ"
    }
    ```
    """
    company = await company_crud.get_by_ticker(db, ticker.upper())

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{ticker}' not found",
        )

    return CompanyResponse(
        ticker=company.ticker,
        cik=company.cik,
        company_name=company.company_name,
        exchange=company.exchange,
    )


@router.get("/search/name", response_model=list[CompanyResponse])
async def search_companies(
    q: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_current_db),
    api_key: str = Depends(require_api_key),
) -> list[CompanyResponse]:
    """
    Search for companies by name (partial match).

    **Parameters:**
    - **q**: Search query string
    - **limit**: Maximum number of results (default: 10)

    **Returns:**
    - List of matching companies
    """
    companies = await company_crud.search_by_name(db, q, limit)

    return [
        CompanyResponse(
            ticker=c.ticker,
            cik=c.cik,
            company_name=c.company_name,
            exchange=c.exchange,
        )
        for c in companies
    ]
