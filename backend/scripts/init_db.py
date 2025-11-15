"""
Initialize the database with schema and sample data.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine, AsyncSessionLocal, init_db
from app.core.config import settings


async def create_schema():
    """Create database schema from SQL file."""
    schema_file = Path(__file__).parent.parent.parent / "database" / "schema.sql"

    if not schema_file.exists():
        print(f"Schema file not found: {schema_file}")
        return False

    print(f"Reading schema from {schema_file}")

    with open(schema_file, "r") as f:
        schema_sql = f.read()

    # Split into individual statements
    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]

    async with engine.begin() as conn:
        for statement in statements:
            if statement:
                try:
                    await conn.execute(text(statement))
                    print(f"Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"Error executing statement: {e}")
                    print(f"Statement: {statement[:100]}")

    print("Schema created successfully!")
    return True


async def create_sample_data():
    """Create sample data for testing."""
    async with AsyncSessionLocal() as db:
        from app.crud.company import company_crud
        from app.schemas.company import CompanyCreate

        # Add some sample companies
        sample_companies = [
            {
                "ticker": "AAPL",
                "cik": "0000320193",
                "company_name": "Apple Inc.",
                "exchange": "NASDAQ",
            },
            {
                "ticker": "MSFT",
                "cik": "0000789019",
                "company_name": "Microsoft Corporation",
                "exchange": "NASDAQ",
            },
            {
                "ticker": "GOOGL",
                "cik": "0001652044",
                "company_name": "Alphabet Inc.",
                "exchange": "NASDAQ",
            },
        ]

        for company_data in sample_companies:
            try:
                # Check if exists
                existing = await company_crud.get_by_ticker(db, company_data["ticker"])
                if not existing:
                    company = CompanyCreate(**company_data)
                    await company_crud.create(db, company)
                    print(f"Created sample company: {company_data['ticker']}")
                else:
                    print(f"Company already exists: {company_data['ticker']}")
            except Exception as e:
                print(f"Error creating company {company_data['ticker']}: {e}")

        await db.commit()


async def main():
    """Main initialization function."""
    print("=" * 50)
    print("US Financial Statement Database - Initialization")
    print("=" * 50)
    print(f"Database URL: {settings.DATABASE_URL}")
    print()

    # Create schema
    await create_schema()

    # Create sample data
    print("\nCreating sample data...")
    await create_sample_data()

    print("\n" + "=" * 50)
    print("Initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
