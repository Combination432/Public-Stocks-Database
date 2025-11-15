"""Filing schemas."""
from datetime import date
from typing import List

from pydantic import BaseModel, Field, field_validator


class FilingBase(BaseModel):
    """Base filing schema."""

    filing_type: str = Field(..., pattern="^(10-K|10-Q)$", description="Filing type")
    filing_date: date = Field(..., description="Date the filing was submitted")
    period_end_date: date = Field(..., description="Period end date")
    period_year: int = Field(..., ge=1990, le=2100, description="Fiscal year")
    period_quarter: int | None = Field(
        None, ge=1, le=4, description="Fiscal quarter (1-4, null for annual)"
    )
    accession_number: str | None = Field(None, max_length=50)
    document_url: str | None = None
    is_restatement: bool = False


class FilingCreate(FilingBase):
    """Schema for creating a filing."""

    company_id: int


class Filing(FilingBase):
    """Schema for filing with ID."""

    filing_id: int
    company_id: int

    class Config:
        from_attributes = True


class FilingResponse(BaseModel):
    """API response schema for a single filing."""

    filing_id: int
    filing_type: str
    filing_date: date
    period_year: int
    period_quarter: int | None

    class Config:
        from_attributes = True


class FilingList(BaseModel):
    """API response schema for list of filings."""

    ticker: str
    filings: List[FilingResponse]
