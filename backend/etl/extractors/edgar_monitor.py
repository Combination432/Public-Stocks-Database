"""
SEC EDGAR filing monitor.

Monitors the SEC EDGAR RSS feed for new 10-K and 10-Q filings.
"""
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings


class EdgarMonitor:
    """
    Monitor SEC EDGAR for new filings.

    Uses the SEC EDGAR RSS feeds to detect new 10-K and 10-Q filings.
    """

    RSS_FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    COMPANY_SEARCH_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

    def __init__(self):
        """Initialize the EDGAR monitor."""
        self.session = self._create_session()
        self.headers = {
            "User-Agent": settings.SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _rate_limit(self):
        """Rate limit requests to SEC (max 10 requests per second)."""
        time.sleep(settings.SEC_RATE_LIMIT_DELAY)

    def get_company_cik(self, ticker: str) -> str | None:
        """
        Get CIK for a company by ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK number or None if not found
        """
        self._rate_limit()

        # SEC provides a JSON endpoint for company tickers
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=&dateb=&owner=exclude&count=1&output=atom"

        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)
            # Extract CIK from company-info
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            cik_elem = root.find(".//atom:company-info/atom:cik", ns)

            if cik_elem is not None:
                return cik_elem.text.zfill(10)  # Pad to 10 digits

        except Exception as e:
            print(f"Error fetching CIK for {ticker}: {e}")

        return None

    def get_recent_filings(
        self, cik: str, filing_types: List[str] = None, count: int = 100
    ) -> List[Dict]:
        """
        Get recent filings for a company.

        Args:
            cik: Company CIK number
            filing_types: List of filing types to filter (e.g., ['10-K', '10-Q'])
            count: Number of filings to retrieve

        Returns:
            List of filing metadata dictionaries
        """
        if filing_types is None:
            filing_types = ["10-K", "10-Q"]

        self._rate_limit()

        filings = []
        for filing_type in filing_types:
            url = (
                f"https://www.sec.gov/cgi-bin/browse-edgar"
                f"?action=getcompany&CIK={cik}&type={filing_type}"
                f"&dateb=&owner=exclude&count={count}&output=atom"
            )

            try:
                response = self.session.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()

                # Parse XML response
                root = ET.fromstring(response.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}

                # Extract entries
                for entry in root.findall("atom:entry", ns):
                    filing_data = self._parse_filing_entry(entry, ns)
                    if filing_data:
                        filings.append(filing_data)

            except Exception as e:
                print(f"Error fetching filings for CIK {cik}, type {filing_type}: {e}")

        # Sort by filing date (most recent first)
        filings.sort(key=lambda x: x["filing_date"], reverse=True)
        return filings[:count]

    def _parse_filing_entry(self, entry: ET.Element, ns: dict) -> Dict | None:
        """
        Parse a single filing entry from XML.

        Args:
            entry: XML entry element
            ns: XML namespace dictionary

        Returns:
            Filing metadata dictionary or None
        """
        try:
            # Extract filing data
            filing_type = entry.find("atom:category", ns).get("term")
            filing_date = entry.find("atom:updated", ns).text[:10]  # YYYY-MM-DD
            accession_number = entry.find("atom:id", ns).text.split("/")[-1]

            # Extract filing URL
            link = entry.find("atom:link[@type='text/html']", ns)
            filing_url = link.get("href") if link is not None else None

            # Extract period (if available in summary)
            summary = entry.find("atom:summary", ns)
            period_end_date = self._extract_period_from_summary(summary.text if summary is not None else "")

            return {
                "filing_type": filing_type,
                "filing_date": datetime.strptime(filing_date, "%Y-%m-%d").date(),
                "accession_number": accession_number,
                "filing_url": filing_url,
                "period_end_date": period_end_date,
            }

        except Exception as e:
            print(f"Error parsing filing entry: {e}")
            return None

    def _extract_period_from_summary(self, summary: str) -> str | None:
        """Extract period end date from filing summary."""
        # Look for pattern like "Filed on 2024-01-26 for the period ending 2023-12-30"
        match = re.search(r"period ending (\d{4}-\d{2}-\d{2})", summary)
        if match:
            return match.group(1)
        return None

    def get_filings_since(self, since_date: datetime, filing_types: List[str] = None) -> List[Dict]:
        """
        Get all new filings since a specific date.

        This is a placeholder for monitoring new filings. In production,
        you would use the SEC EDGAR RSS feed or the EDGAR API.

        Args:
            since_date: Get filings since this date
            filing_types: List of filing types to monitor

        Returns:
            List of new filings
        """
        if filing_types is None:
            filing_types = ["10-K", "10-Q"]

        # TODO: Implement RSS feed monitoring
        # For now, this is a placeholder
        print(f"Monitoring for new filings since {since_date}...")
        return []

    def get_filing_document_url(self, accession_number: str, cik: str) -> str:
        """
        Get the direct URL to the filing document.

        Args:
            accession_number: SEC accession number
            cik: Company CIK

        Returns:
            URL to the filing document
        """
        # Remove dashes from accession number
        accession_clean = accession_number.replace("-", "")
        cik_padded = cik.zfill(10)

        # Construct URL to the filing index
        base_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik_padded}&accession_number={accession_number}"

        return base_url


# Global instance
edgar_monitor = EdgarMonitor()
