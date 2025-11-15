"""
Database loader for ETL pipeline.

Loads parsed financial data into the database.
"""
from datetime import date
from decimal import Decimal
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.company import company_crud
from app.crud.filing import filing_crud
from app.crud.financial_data import financial_data_crud
from app.schemas.company import CompanyCreate
from app.schemas.filing import FilingCreate
from app.schemas.financial_data import FinancialDataCreate


class DatabaseLoader:
    """Load financial data into the database."""

    async def load_company(
        self, db: AsyncSession, ticker: str, cik: str, name: str = None, exchange: str = None
    ) -> int:
        """
        Create or update a company record.

        Args:
            db: Database session
            ticker: Stock ticker
            cik: CIK number
            name: Company name
            exchange: Stock exchange

        Returns:
            Company ID
        """
        # Check if company exists
        existing = await company_crud.get_by_ticker(db, ticker)

        if existing:
            # Update if needed
            if name and existing.company_name != name:
                await company_crud.update(db, existing, {"company_name": name})
            return existing.company_id

        # Create new company
        company_data = CompanyCreate(
            ticker=ticker.upper(),
            cik=cik,
            company_name=name,
            exchange=exchange,
        )

        company = await company_crud.create(db, company_data)
        return company.company_id

    async def load_filing(
        self,
        db: AsyncSession,
        company_id: int,
        filing_type: str,
        filing_date: date,
        period_end_date: date,
        period_year: int,
        period_quarter: int | None,
        accession_number: str = None,
        document_url: str = None,
    ) -> int:
        """
        Create or update a filing record.

        Args:
            db: Database session
            company_id: Company ID
            filing_type: '10-K' or '10-Q'
            filing_date: Filing date
            period_end_date: Period end date
            period_year: Fiscal year
            period_quarter: Fiscal quarter (or None for annual)
            accession_number: SEC accession number
            document_url: URL to the filing

        Returns:
            Filing ID
        """
        filing_data = FilingCreate(
            company_id=company_id,
            filing_type=filing_type,
            filing_date=filing_date,
            period_end_date=period_end_date,
            period_year=period_year,
            period_quarter=period_quarter,
            accession_number=accession_number,
            document_url=document_url,
            is_restatement=False,
        )

        # Upsert filing (handles restatements)
        filing, created = await filing_crud.upsert_filing(db, filing_data)
        return filing.filing_id

    async def load_financial_data(
        self,
        db: AsyncSession,
        filing_id: int,
        statement_type: str,
        line_items: List[Dict],
    ) -> int:
        """
        Load financial data for a filing.

        Args:
            db: Database session
            filing_id: Filing ID
            statement_type: 'IS', 'BS', or 'CF'
            line_items: List of line items with name, value, order

        Returns:
            Number of records created
        """
        # Delete existing data for this filing/statement (in case of restatement)
        await financial_data_crud.delete_filing_data(db, filing_id)

        # Create financial data records
        data_records = []
        for item in line_items:
            record = FinancialDataCreate(
                filing_id=filing_id,
                statement_type=statement_type,
                line_item_name=item.get("line_item_name", ""),
                value=Decimal(str(item["value"])) if item.get("value") is not None else None,
                display_order=item.get("display_order"),
                unit=item.get("unit", "USD"),
            )
            data_records.append(record)

        # Bulk insert
        if data_records:
            await financial_data_crud.create_many(db, data_records)

        return len(data_records)

    async def load_complete_filing(
        self,
        db: AsyncSession,
        ticker: str,
        cik: str,
        company_name: str,
        exchange: str,
        filing_type: str,
        filing_date: date,
        period_end_date: date,
        period_year: int,
        period_quarter: int | None,
        accession_number: str,
        document_url: str,
        statements: Dict[str, List[Dict]],
    ) -> Dict:
        """
        Load a complete filing with all financial data.

        Args:
            db: Database session
            ticker: Stock ticker
            cik: CIK number
            company_name: Company name
            exchange: Stock exchange
            filing_type: '10-K' or '10-Q'
            filing_date: Filing date
            period_end_date: Period end date
            period_year: Fiscal year
            period_quarter: Fiscal quarter
            accession_number: SEC accession number
            document_url: Filing URL
            statements: Dictionary with 'IS', 'BS', 'CF' data

        Returns:
            Dictionary with loading results
        """
        results = {
            "success": False,
            "company_id": None,
            "filing_id": None,
            "records_created": 0,
            "errors": [],
        }

        try:
            # Load company
            company_id = await self.load_company(
                db, ticker, cik, company_name, exchange
            )
            results["company_id"] = company_id

            # Load filing
            filing_id = await self.load_filing(
                db,
                company_id,
                filing_type,
                filing_date,
                period_end_date,
                period_year,
                period_quarter,
                accession_number,
                document_url,
            )
            results["filing_id"] = filing_id

            # Load financial data for each statement
            total_records = 0
            for statement_type, line_items in statements.items():
                if line_items:
                    count = await self.load_financial_data(
                        db, filing_id, statement_type, line_items
                    )
                    total_records += count

            results["records_created"] = total_records
            results["success"] = True

            # Commit transaction
            await db.commit()

        except Exception as e:
            results["errors"].append(str(e))
            await db.rollback()
            raise

        return results


# Global instance
db_loader = DatabaseLoader()
