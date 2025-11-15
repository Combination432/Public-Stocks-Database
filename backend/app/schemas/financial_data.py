"""Financial data schemas."""
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field


class FinancialDataBase(BaseModel):
    """Base financial data schema."""

    statement_type: str = Field(
        ..., pattern="^(IS|BS|CF)$", description="Statement type: IS, BS, or CF"
    )
    line_item_name: str = Field(..., max_length=500, description="As-reported line item name")
    value: Decimal | None = Field(None, description="Numerical value")
    display_order: int | None = Field(None, description="Display order on statement")
    unit: str = Field(default="USD", max_length=20)


class FinancialDataCreate(FinancialDataBase):
    """Schema for creating financial data."""

    filing_id: int


class FinancialData(FinancialDataBase):
    """Schema for financial data with ID."""

    data_id: int
    filing_id: int

    class Config:
        from_attributes = True


class LineItem(BaseModel):
    """Schema for a single line item in a statement."""

    line_item_name: str
    value: float | None
    order: int | None = Field(None, alias="display_order")

    class Config:
        from_attributes = True
        populate_by_name = True


class StatementResponse(BaseModel):
    """API response schema for a full financial statement."""

    ticker: str
    statement_type: str = Field(
        ..., description="Statement type: income_statement, balance_sheet, or cash_flow"
    )
    period_year: int
    period_quarter: int | None
    data: List[LineItem]

    class Config:
        from_attributes = True


class TimeSeriesDataPoint(BaseModel):
    """A single data point in a time series."""

    year: int
    quarter: int | None
    value: float | None


class TimeSeriesResponse(BaseModel):
    """API response schema for time series data."""

    ticker: str
    line_item_name: str
    period_type: str = Field(..., description="quarterly or annual")
    history: List[TimeSeriesDataPoint]

    class Config:
        from_attributes = True
