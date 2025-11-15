"""CRUD operations for FinancialData model."""
from typing import List, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_data import FinancialData
from app.models.filing import Filing
from app.schemas.financial_data import FinancialDataCreate


class FinancialDataCRUD:
    """CRUD operations for FinancialData."""

    async def get_by_id(self, db: AsyncSession, data_id: int) -> Optional[FinancialData]:
        """Get financial data by ID."""
        result = await db.execute(
            select(FinancialData).where(FinancialData.data_id == data_id)
        )
        return result.scalar_one_or_none()

    async def get_statement_data(
        self,
        db: AsyncSession,
        filing_id: int,
        statement_type: str,
    ) -> List[FinancialData]:
        """Get all line items for a specific statement."""
        result = await db.execute(
            select(FinancialData)
            .where(
                and_(
                    FinancialData.filing_id == filing_id,
                    FinancialData.statement_type == statement_type,
                )
            )
            .order_by(FinancialData.display_order)
        )
        return list(result.scalars().all())

    async def get_line_item_history(
        self,
        db: AsyncSession,
        company_id: int,
        line_item_name: str,
        statement_type: str,
        period_type: str = "quarterly",  # 'quarterly' or 'annual'
        limit: int = 100,
    ) -> List[tuple[Filing, FinancialData]]:
        """
        Get time series data for a specific line item.

        Returns list of (Filing, FinancialData) tuples ordered by period desc.
        """
        filing_type = "10-K" if period_type == "annual" else "10-Q"

        query = (
            select(Filing, FinancialData)
            .join(FinancialData, Filing.filing_id == FinancialData.filing_id)
            .where(
                and_(
                    Filing.company_id == company_id,
                    Filing.filing_type == filing_type,
                    FinancialData.statement_type == statement_type,
                    FinancialData.line_item_name == line_item_name,
                )
            )
            .order_by(desc(Filing.period_year), desc(Filing.period_quarter))
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.all())

    async def search_line_items(
        self,
        db: AsyncSession,
        company_id: int,
        search_term: str,
        limit: int = 50,
    ) -> List[str]:
        """
        Search for line item names containing the search term.
        Returns unique line item names.
        """
        query = (
            select(FinancialData.line_item_name)
            .distinct()
            .join(Filing, FinancialData.filing_id == Filing.filing_id)
            .where(
                and_(
                    Filing.company_id == company_id,
                    FinancialData.line_item_name.ilike(f"%{search_term}%"),
                )
            )
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: FinancialDataCreate) -> FinancialData:
        """Create a new financial data entry."""
        db_obj = FinancialData(
            filing_id=obj_in.filing_id,
            statement_type=obj_in.statement_type,
            line_item_name=obj_in.line_item_name,
            value=obj_in.value,
            display_order=obj_in.display_order,
            unit=obj_in.unit,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def create_many(
        self, db: AsyncSession, objects_in: List[FinancialDataCreate]
    ) -> List[FinancialData]:
        """Bulk create financial data entries."""
        db_objs = [
            FinancialData(
                filing_id=obj.filing_id,
                statement_type=obj.statement_type,
                line_item_name=obj.line_item_name,
                value=obj.value,
                display_order=obj.display_order,
                unit=obj.unit,
            )
            for obj in objects_in
        ]
        db.add_all(db_objs)
        await db.flush()
        return db_objs

    async def delete_filing_data(self, db: AsyncSession, filing_id: int) -> int:
        """Delete all financial data for a filing. Returns count of deleted records."""
        result = await db.execute(
            select(FinancialData).where(FinancialData.filing_id == filing_id)
        )
        records = result.scalars().all()
        count = len(records)
        for record in records:
            await db.delete(record)
        await db.flush()
        return count


# Global instance
financial_data_crud = FinancialDataCRUD()
