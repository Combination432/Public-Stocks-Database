"""
Backfill script to populate database with historical data.

Usage:
    python scripts/backfill.py --ticker AAPL --years 10
    python scripts/backfill.py --file tickers.txt --years 5
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.extractors.edgar_monitor import edgar_monitor
from etl.tasks import backfill_company


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Backfill historical financial data")

    parser.add_argument(
        "--ticker", type=str, help="Single ticker to backfill (e.g., AAPL)"
    )
    parser.add_argument(
        "--file", type=str, help="File with list of tickers (one per line)"
    )
    parser.add_argument(
        "--years", type=int, default=10, help="Number of years to backfill (default: 10)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of tickers to process in parallel (default: 10)",
    )

    return parser.parse_args()


def get_tickers(args):
    """Get list of tickers to process."""
    tickers = []

    if args.ticker:
        tickers.append(args.ticker.upper())
    elif args.file:
        with open(args.file, "r") as f:
            tickers = [line.strip().upper() for line in f if line.strip()]
    else:
        print("Error: Must specify either --ticker or --file")
        sys.exit(1)

    return tickers


def main():
    """Main backfill function."""
    args = parse_args()
    tickers = get_tickers(args)

    print("=" * 60)
    print("US Financial Statement Database - Historical Data Backfill")
    print("=" * 60)
    print(f"Tickers to process: {len(tickers)}")
    print(f"Years to backfill: {args.years}")
    print(f"Batch size: {args.batch_size}")
    print()

    # Process tickers in batches
    total_processed = 0
    total_errors = 0

    for i in range(0, len(tickers), args.batch_size):
        batch = tickers[i : i + args.batch_size]
        print(f"\nProcessing batch {i // args.batch_size + 1}: {', '.join(batch)}")

        for ticker in batch:
            try:
                # Get CIK for ticker
                cik = edgar_monitor.get_company_cik(ticker)

                if not cik:
                    print(f"  ✗ {ticker}: Could not find CIK")
                    total_errors += 1
                    continue

                print(f"  → {ticker} (CIK: {cik})")

                # Run backfill task (synchronously for now)
                result = backfill_company(ticker, cik, args.years)

                if result.get("errors"):
                    print(f"    ✗ Errors: {len(result['errors'])}")
                    for error in result["errors"][:3]:  # Show first 3 errors
                        print(f"      - {error}")
                    total_errors += 1
                else:
                    print(
                        f"    ✓ Processed {result['filings_processed']}/{result['filings_found']} filings"
                    )
                    total_processed += 1

            except Exception as e:
                print(f"  ✗ {ticker}: {str(e)}")
                total_errors += 1

    print("\n" + "=" * 60)
    print("Backfill Summary")
    print("=" * 60)
    print(f"Total tickers: {len(tickers)}")
    print(f"Successfully processed: {total_processed}")
    print(f"Errors: {total_errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
