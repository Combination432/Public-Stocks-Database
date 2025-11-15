"""CRUD operations for Filing model."""
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.filing import Filing
from app.schemas.filing import FilingCreate


class FilingCRUD:
    """CRUD operations for Filing."""

    async def get_by_id(
        self, db: AsyncSession, filing_id: int, load_data: bool = False
    ) -> Optional[Filing]:
        """Get filing by ID."""
        query = select(Filing).where(Filing.filing_id == filing_id)
        if load_data:
            query = query.options(selectinload(Filing.financial_data))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_accession(self, db: AsyncSession, accession_number: str) -> Optional[Filing]:
        """Get filing by SEC accession number."""
        result = await db.execute(
            select(Filing).where(Filing.accession_number == accession_number)
        )
        return result.scalar_one_or_none()

    async def get_company_filings(
        self,
        db: AsyncSession,
        company_id: int,
        filing_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Filing]:
        """Get all filings for a company."""
        query = select(Filing).where(Filing.company_id == company_id)
        if filing_type:
            query = query.where(Filing.filing_type == filing_type)
        query = query.order_by(desc(Filing.filing_date)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_filing_for_period(
        self,
        db: AsyncSession,
        company_id: int,
        year: int,
        quarter: Optional[int] = None,
    ) -> Optional[Filing]:
        """Get the most recent filing for a specific period."""
        query = (
            select(Filing)
            .where(
                and_(
                    Filing.company_id == company_id,
                    Filing.period_year == year,
                    Filing.period_quarter == quarter,
                )
            )
            .order_by(desc(Filing.filing_date))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_recent_filings(
        self, db: AsyncSession, since_date: date, limit: int = 100
    ) -> List[Filing]:
        """Get recent filings since a specific date."""
        query = (
            select(Filing)
            .where(Filing.filing_date >= since_date)
            .order_by(desc(Filing.filing_date))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: FilingCreate) -> Filing:
        """Create a new filing."""
        db_obj = Filing(
            company_id=obj_in.company_id,
            filing_type=obj_in.filing_type,
            filing_date=obj_in.filing_date,
            period_end_date=obj_in.period_end_date,
            period_year=obj_in.period_year,
            period_quarter=obj_in.period_quarter,
            accession_number=obj_in.accession_number,
            document_url=obj_in.document_url,
            is_restatement=obj_in.is_restatement,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def upsert_filing(
        self, db: AsyncSession, obj_in: FilingCreate
    ) -> tuple[Filing, bool]:
        """
        Create or update a filing for a given period.
        Returns (filing, created) where created is True if new, False if updated.
        """
        existing = await self.get_filing_for_period(
            db, obj_in.company_id, obj_in.period_year, obj_in.period_quarter
        )

        if existing:
            # Update if this is a newer filing for the same period (restatement)
            if obj_in.filing_date >= existing.filing_date:
                existing.filing_date = obj_in.filing_date
                existing.period_end_date = obj_in.period_end_date
                existing.accession_number = obj_in.accession_number
                existing.document_url = obj_in.document_url
                existing.is_restatement = True
                await db.flush()
                await db.refresh(existing)
                return existing, False
            return existing, False
        else:
            return await self.create(db, obj_in), True


# Global instance
filing_crud = FilingCRUD()
