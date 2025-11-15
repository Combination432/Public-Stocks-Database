"""Filing model."""
from datetime import datetime, date
from typing import List, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.financial_data import FinancialData


class Filing(Base):
    """
    Represents a single SEC filing (10-K or 10-Q).

    Links to a company and contains metadata about the filing period.
    """

    __tablename__ = "filing"
    __table_args__ = (
        CheckConstraint("filing_type IN ('10-K', '10-Q')", name="valid_filing_type"),
        CheckConstraint(
            "period_quarter IS NULL OR period_quarter BETWEEN 1 AND 4",
            name="valid_quarter",
        ),
        UniqueConstraint(
            "company_id",
            "period_year",
            "period_quarter",
            "filing_date",
            name="unique_filing",
        ),
    )

    filing_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("company.company_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filing_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_quarter: Mapped[int | None] = mapped_column(Integer)
    accession_number: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    document_url: Mapped[str | None] = mapped_column(Text)
    is_restatement: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="filings")
    financial_data: Mapped[List["FinancialData"]] = relationship(
        "FinancialData", back_populates="filing", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Filing(type={self.filing_type}, "
            f"period={self.period_year}Q{self.period_quarter or 'Annual'})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "filing_id": self.filing_id,
            "filing_type": self.filing_type,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "period_end_date": self.period_end_date.isoformat() if self.period_end_date else None,
            "period_year": self.period_year,
            "period_quarter": self.period_quarter,
            "accession_number": self.accession_number,
            "document_url": self.document_url,
            "is_restatement": self.is_restatement,
        }
