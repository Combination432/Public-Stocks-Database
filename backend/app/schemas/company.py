"""Company schemas."""
from pydantic import BaseModel, Field


class CompanyBase(BaseModel):
    """Base company schema."""

    ticker: str = Field(..., max_length=10, description="Stock ticker symbol")
    cik: str = Field(..., max_length=20, description="SEC CIK number")
    company_name: str | None = Field(None, max_length=255, description="Company name")
    exchange: str | None = Field(None, max_length=50, description="Stock exchange")


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""

    pass


class Company(CompanyBase):
    """Schema for company with ID."""

    company_id: int

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    """API response schema for company metadata."""

    ticker: str
    cik: str
    company_name: str | None
    exchange: str | None

    class Config:
        from_attributes = True
