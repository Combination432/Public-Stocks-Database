"""
SEC EDGAR filing downloader.

Downloads filing documents from SEC EDGAR.
"""
import os
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings


class FilingDownloader:
    """Download filings from SEC EDGAR."""

    def __init__(self, download_dir: str = "/tmp/edgar_filings"):
        """
        Initialize the filing downloader.

        Args:
            download_dir: Directory to store downloaded filings
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = self._create_session()
        self.headers = {
            "User-Agent": settings.SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
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
        """Rate limit requests to SEC."""
        time.sleep(settings.SEC_RATE_LIMIT_DELAY)

    def download_filing(self, accession_number: str, cik: str) -> Optional[str]:
        """
        Download a filing and return the local file path.

        Args:
            accession_number: SEC accession number
            cik: Company CIK

        Returns:
            Path to downloaded file or None if failed
        """
        self._rate_limit()

        # Clean accession number (remove dashes)
        accession_clean = accession_number.replace("-", "")
        cik_padded = cik.zfill(10)

        # Construct URL to the complete filing
        # Try to get the XBRL instance document first
        filing_dir = f"{cik_padded}/{accession_clean}"
        xbrl_filename = f"{accession_clean}.xml"  # Typical XBRL instance document name

        # Try different URL patterns
        urls_to_try = [
            f"https://www.sec.gov/Archives/edgar/data/{filing_dir}/{xbrl_filename}",
            f"https://www.sec.gov/Archives/edgar/data/{filing_dir}/{accession_number}-xbrl.xml",
            f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik_padded}&accession_number={accession_number}&xbrl_type=v",
        ]

        for url in urls_to_try:
            try:
                response = self.session.get(url, headers=self.headers, timeout=30)
                if response.status_code == 200:
                    # Save to file
                    filename = f"{accession_clean}.xml"
                    filepath = self.download_dir / filename

                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    print(f"Downloaded filing {accession_number} to {filepath}")
                    return str(filepath)

            except Exception as e:
                print(f"Error downloading from {url}: {e}")
                continue

        print(f"Failed to download filing {accession_number}")
        return None

    def download_filing_index(self, accession_number: str, cik: str) -> Optional[dict]:
        """
        Download the filing index to find all documents.

        Args:
            accession_number: SEC accession number
            cik: Company CIK

        Returns:
            Dictionary with filing document URLs
        """
        self._rate_limit()

        accession_clean = accession_number.replace("-", "")
        cik_padded = cik.zfill(10)

        # Get the index page
        index_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik_padded}&accession_number={accession_number}&xbrl_type=v"

        try:
            response = self.session.get(index_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # TODO: Parse HTML to extract document URLs
            # For now, return the index URL
            return {
                "index_url": index_url,
                "accession_number": accession_number,
            }

        except Exception as e:
            print(f"Error fetching filing index: {e}")
            return None

    def get_xbrl_instance_url(self, cik: str, accession_number: str) -> str:
        """
        Get the URL for the XBRL instance document.

        Args:
            cik: Company CIK
            accession_number: SEC accession number

        Returns:
            URL to the XBRL instance document
        """
        accession_clean = accession_number.replace("-", "")
        cik_padded = cik.zfill(10)

        # Standard XBRL instance document location
        return f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik_padded}&accession_number={accession_number}&xbrl_type=v"

    def cleanup_old_files(self, days: int = 7):
        """
        Clean up downloaded files older than specified days.

        Args:
            days: Remove files older than this many days
        """
        cutoff_time = time.time() - (days * 86400)

        for filepath in self.download_dir.glob("*.xml"):
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    print(f"Removed old file: {filepath}")
                except Exception as e:
                    print(f"Error removing file {filepath}: {e}")


# Global instance
filing_downloader = FilingDownloader()
