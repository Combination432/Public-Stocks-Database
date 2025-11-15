"""Financial data model."""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.filing import Filing


class FinancialData(Base):
    """
    Represents a single line item from a financial statement.

    Stores the as-reported line item name and value.
    """

    __tablename__ = "financial_data"
    __table_args__ = (
        CheckConstraint(
            "statement_type IN ('IS', 'BS', 'CF')", name="valid_statement_type"
        ),
        UniqueConstraint(
            "filing_id", "statement_type", "line_item_name", name="unique_line_item"
        ),
    )

    data_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filing_id: Mapped[int] = mapped_column(
        ForeignKey("filing.filing_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement_type: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    line_item_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    display_order: Mapped[int | None] = mapped_column(Integer)
    unit: Mapped[str] = mapped_column(String(20), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    filing: Mapped["Filing"] = relationship("Filing", back_populates="financial_data")

    def __repr__(self) -> str:
        return (
            f"<FinancialData(statement={self.statement_type}, "
            f"item={self.line_item_name[:30]}, value={self.value})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "data_id": self.data_id,
            "filing_id": self.filing_id,
            "statement_type": self.statement_type,
            "line_item_name": self.line_item_name,
            "value": float(self.value) if self.value is not None else None,
            "display_order": self.display_order,
            "unit": self.unit,
        }
