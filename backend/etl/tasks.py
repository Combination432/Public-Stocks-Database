"""
Celery tasks for ETL automation.

Defines background tasks for monitoring and processing SEC filings.
"""
from datetime import datetime, timedelta
from typing import Dict, List

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from etl.extractors.edgar_monitor import edgar_monitor
from etl.extractors.filing_downloader import filing_downloader
from etl.extractors.xbrl_parser import xbrl_parser
from etl.loaders.db_loader import db_loader
from etl.validators.data_validator import DataValidator

# Create Celery app
celery_app = Celery(
    "financial_etl",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    "monitor-new-filings": {
        "task": "etl.tasks.monitor_new_filings",
        "schedule": settings.ETL_CHECK_INTERVAL,  # Every hour by default
    },
    "cleanup-downloads": {
        "task": "etl.tasks.cleanup_downloads",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}


@celery_app.task(name="etl.tasks.process_filing")
def process_filing(ticker: str, cik: str, filing_metadata: Dict) -> Dict:
    """
    Process a single SEC filing.

    Args:
        ticker: Stock ticker
        cik: CIK number
        filing_metadata: Filing metadata from EDGAR monitor

    Returns:
        Processing results
    """
    import asyncio

    print(f"Processing filing for {ticker}: {filing_metadata.get('accession_number')}")

    results = {
        "ticker": ticker,
        "accession_number": filing_metadata.get("accession_number"),
        "success": False,
        "errors": [],
    }

    try:
        # Download filing
        filepath = filing_downloader.download_filing(
            filing_metadata["accession_number"], cik
        )

        if not filepath:
            results["errors"].append("Failed to download filing")
            return results

        # Parse XBRL
        parsed_data = xbrl_parser.parse_filing_file(filepath)

        if "error" in parsed_data:
            results["errors"].append(f"Parsing error: {parsed_data['error']}")
            return results

        # Extract financial statements
        period_end_date = filing_metadata.get("period_end_date") or filing_metadata["filing_date"]
        statements = xbrl_parser.extract_financial_statements(
            parsed_data, str(period_end_date)
        )

        # Validate data
        validator = DataValidator()
        validation_results = validator.validate_all_statements(statements)

        if not validation_results["valid"]:
            results["errors"].extend(validation_results["errors"])
            # Continue anyway, but log errors

        if validation_results["warnings"]:
            results["warnings"] = validation_results["warnings"]

        # Determine period year and quarter
        filing_type = filing_metadata["filing_type"]
        period_year = period_end_date.year
        period_quarter = None

        if filing_type == "10-Q":
            # Determine quarter from month
            month = period_end_date.month
            if month <= 3:
                period_quarter = 1
            elif month <= 6:
                period_quarter = 2
            elif month <= 9:
                period_quarter = 3
            else:
                period_quarter = 4

        # Load into database
        async def load_data():
            async with AsyncSessionLocal() as db:
                return await db_loader.load_complete_filing(
                    db=db,
                    ticker=ticker,
                    cik=cik,
                    company_name=None,  # Will be fetched if needed
                    exchange=None,
                    filing_type=filing_type,
                    filing_date=filing_metadata["filing_date"],
                    period_end_date=period_end_date,
                    period_year=period_year,
                    period_quarter=period_quarter,
                    accession_number=filing_metadata["accession_number"],
                    document_url=filing_metadata.get("filing_url"),
                    statements=statements,
                )

        load_results = asyncio.run(load_data())

        results.update(load_results)
        results["success"] = load_results["success"]

        print(
            f"Successfully processed {ticker} filing: "
            f"{load_results['records_created']} records created"
        )

    except Exception as e:
        results["errors"].append(str(e))
        print(f"Error processing filing for {ticker}: {e}")

    return results


@celery_app.task(name="etl.tasks.monitor_new_filings")
def monitor_new_filings() -> Dict:
    """
    Monitor for new filings and queue them for processing.

    Returns:
        Dictionary with monitoring results
    """
    print("Monitoring for new filings...")

    results = {
        "checked_at": datetime.utcnow().isoformat(),
        "new_filings": 0,
        "queued": 0,
    }

    try:
        # Get filings from the last check interval (plus buffer)
        since_date = datetime.utcnow() - timedelta(
            seconds=settings.ETL_CHECK_INTERVAL + 300
        )

        # TODO: Implement actual RSS feed monitoring
        # For now, this is a placeholder
        new_filings = edgar_monitor.get_filings_since(since_date)

        results["new_filings"] = len(new_filings)

        # Queue each new filing for processing
        for filing in new_filings:
            # Extract ticker and CIK from filing metadata
            # This is a simplified version - actual implementation would need more logic
            ticker = filing.get("ticker")
            cik = filing.get("cik")

            if ticker and cik:
                process_filing.delay(ticker, cik, filing)
                results["queued"] += 1

        print(f"Queued {results['queued']} new filings for processing")

    except Exception as e:
        print(f"Error monitoring new filings: {e}")
        results["error"] = str(e)

    return results


@celery_app.task(name="etl.tasks.backfill_company")
def backfill_company(ticker: str, cik: str, years: int = 10) -> Dict:
    """
    Backfill historical filings for a company.

    Args:
        ticker: Stock ticker
        cik: CIK number
        years: Number of years to backfill

    Returns:
        Backfill results
    """
    print(f"Starting backfill for {ticker} ({cik}), {years} years")

    results = {
        "ticker": ticker,
        "cik": cik,
        "years": years,
        "filings_found": 0,
        "filings_processed": 0,
        "errors": [],
    }

    try:
        # Get historical filings
        filings = edgar_monitor.get_recent_filings(
            cik, filing_types=["10-K", "10-Q"], count=years * 5  # ~4 10-Qs + 1 10-K per year
        )

        results["filings_found"] = len(filings)

        # Process each filing
        for filing in filings:
            try:
                result = process_filing(ticker, cik, filing)
                if result["success"]:
                    results["filings_processed"] += 1
            except Exception as e:
                results["errors"].append(
                    f"Filing {filing.get('accession_number')}: {str(e)}"
                )

        print(
            f"Backfill complete for {ticker}: "
            f"{results['filings_processed']}/{results['filings_found']} processed"
        )

    except Exception as e:
        results["errors"].append(str(e))
        print(f"Error during backfill for {ticker}: {e}")

    return results


@celery_app.task(name="etl.tasks.cleanup_downloads")
def cleanup_downloads() -> Dict:
    """
    Clean up old downloaded filing files.

    Returns:
        Cleanup results
    """
    print("Cleaning up old downloaded files...")

    try:
        filing_downloader.cleanup_old_files(days=7)
        return {"success": True, "message": "Cleanup completed"}
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="etl.tasks.refresh_materialized_view")
def refresh_materialized_view() -> Dict:
    """
    Refresh the materialized view for faster queries.

    Returns:
        Refresh results
    """
    import asyncio

    async def refresh():
        async with AsyncSessionLocal() as db:
            await db.execute("SELECT refresh_company_metrics()")
            await db.commit()

    try:
        asyncio.run(refresh())
        return {"success": True, "message": "Materialized view refreshed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
