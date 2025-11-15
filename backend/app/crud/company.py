"""CRUD operations for Company model."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanyCreate


class CompanyCRUD:
    """CRUD operations for Company."""

    async def get_by_id(self, db: AsyncSession, company_id: int) -> Optional[Company]:
        """Get company by ID."""
        result = await db.execute(select(Company).where(Company.company_id == company_id))
        return result.scalar_one_or_none()

    async def get_by_ticker(self, db: AsyncSession, ticker: str) -> Optional[Company]:
        """Get company by ticker symbol."""
        result = await db.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_cik(self, db: AsyncSession, cik: str) -> Optional[Company]:
        """Get company by CIK."""
        result = await db.execute(select(Company).where(Company.cik == cik))
        return result.scalar_one_or_none()

    async def search_by_name(
        self, db: AsyncSession, name: str, limit: int = 10
    ) -> List[Company]:
        """Search companies by name (case-insensitive partial match)."""
        result = await db.execute(
            select(Company)
            .where(Company.company_name.ilike(f"%{name}%"))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_active(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Company]:
        """Get all active companies."""
        result = await db.execute(
            select(Company)
            .where(Company.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: CompanyCreate) -> Company:
        """Create a new company."""
        db_obj = Company(
            ticker=obj_in.ticker.upper(),
            cik=obj_in.cik,
            company_name=obj_in.company_name,
            exchange=obj_in.exchange,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, company: Company, update_data: dict
    ) -> Company:
        """Update a company."""
        for field, value in update_data.items():
            if hasattr(company, field):
                setattr(company, field, value)
        await db.flush()
        await db.refresh(company)
        return company

    async def deactivate(self, db: AsyncSession, company_id: int) -> Optional[Company]:
        """Deactivate a company (soft delete)."""
        company = await self.get_by_id(db, company_id)
        if company:
            company.is_active = False
            await db.flush()
            await db.refresh(company)
        return company


# Global instance
company_crud = CompanyCRUD()
