"""Company model."""
from datetime import datetime
from typing import List

from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Company(Base):
    """
    Represents a publicly traded company.

    Stores basic company information and metadata.
    """

    __tablename__ = "company"

    company_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    cik: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    exchange: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    filings: Mapped[List["Filing"]] = relationship(
        "Filing", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company(ticker={self.ticker}, name={self.company_name})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "company_id": self.company_id,
            "ticker": self.ticker,
            "cik": self.cik,
            "company_name": self.company_name,
            "exchange": self.exchange,
            "is_active": self.is_active,
        }
