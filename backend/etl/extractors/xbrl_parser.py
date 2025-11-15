"""
XBRL parser for SEC filings.

Parses XBRL instance documents to extract financial statement data.
"""
import re
from decimal import Decimal
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

from app.core.config import settings


class XBRLParser:
    """
    Parse XBRL instance documents to extract financial data.

    This parser handles both iXBRL (inline XBRL) and traditional XBRL formats.
    """

    # Common XBRL namespaces
    NAMESPACES = {
        "xbrli": "http://www.xbrl.org/2003/instance",
        "us-gaap": "http://fasb.org/us-gaap/2023",
        "dei": "http://xbrl.sec.gov/dei/2023",
        "xbrldi": "http://xbrl.org/2006/xbrldi",
        "xlink": "http://www.w3.org/1999/xlink",
    }

    # Statement type mapping
    STATEMENT_PATTERNS = {
        "IS": [
            "StatementOfIncome",
            "IncomeStatement",
            "ConsolidatedStatementsOfIncome",
            "ConsolidatedStatementsOfOperations",
            "StatementsOfOperations",
        ],
        "BS": [
            "StatementOfFinancialPosition",
            "BalanceSheet",
            "ConsolidatedBalanceSheets",
            "StatementsOfFinancialPosition",
        ],
        "CF": [
            "StatementOfCashFlows",
            "CashFlowStatement",
            "ConsolidatedStatementsOfCashFlows",
        ],
    }

    def __init__(self):
        """Initialize the XBRL parser."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.SEC_USER_AGENT})

    def parse_filing_url(self, url: str, cik: str, accession_number: str) -> Dict:
        """
        Parse a filing from a URL.

        Args:
            url: URL to the filing
            cik: Company CIK
            accession_number: SEC accession number

        Returns:
            Dictionary containing extracted financial data
        """
        try:
            # Download the filing
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content = response.text

            # Determine if it's iXBRL or traditional XBRL
            if "<html" in content.lower() or "<ix:" in content.lower():
                return self._parse_ixbrl(content)
            else:
                return self._parse_xbrl(content)

        except Exception as e:
            print(f"Error parsing filing from URL {url}: {e}")
            return {"error": str(e)}

    def parse_filing_file(self, filepath: str) -> Dict:
        """
        Parse a filing from a local file.

        Args:
            filepath: Path to the filing file

        Returns:
            Dictionary containing extracted financial data
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Determine format and parse
            if "<html" in content.lower() or "<ix:" in content.lower():
                return self._parse_ixbrl(content)
            else:
                return self._parse_xbrl(content)

        except Exception as e:
            print(f"Error parsing filing from file {filepath}: {e}")
            return {"error": str(e)}

    def _parse_ixbrl(self, content: str) -> Dict:
        """
        Parse inline XBRL (iXBRL) format.

        Args:
            content: HTML/XML content with inline XBRL

        Returns:
            Dictionary with extracted data
        """
        soup = BeautifulSoup(content, "lxml-xml")

        data = {
            "statements": {
                "IS": [],
                "BS": [],
                "CF": [],
            },
            "contexts": {},
            "metadata": {},
        }

        # Extract contexts (periods)
        contexts = soup.find_all("xbrli:context")
        for context in contexts:
            context_id = context.get("id")
            period = context.find("xbrli:period")
            if period:
                instant = period.find("xbrli:instant")
                start = period.find("xbrli:startDate")
                end = period.find("xbrli:endDate")

                data["contexts"][context_id] = {
                    "instant": instant.text if instant else None,
                    "start": start.text if start else None,
                    "end": end.text if end else None,
                }

        # Extract numeric facts
        numeric_facts = soup.find_all(["ix:nonFraction", "xbrli:fact"])

        for fact in numeric_facts:
            try:
                # Get fact details
                name = fact.get("name") or fact.name
                context_ref = fact.get("contextRef")
                value_text = fact.text.strip()

                # Clean and convert value
                value = self._parse_numeric_value(value_text)

                # Determine statement type (simplified)
                statement_type = self._infer_statement_type(name)

                if statement_type:
                    data["statements"][statement_type].append({
                        "name": self._clean_fact_name(name),
                        "value": value,
                        "context": context_ref,
                    })

            except Exception as e:
                continue

        return data

    def _parse_xbrl(self, content: str) -> Dict:
        """
        Parse traditional XBRL format.

        Args:
            content: XML content

        Returns:
            Dictionary with extracted data
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            return {"error": str(e)}

        data = {
            "statements": {
                "IS": [],
                "BS": [],
                "CF": [],
            },
            "contexts": {},
            "metadata": {},
        }

        # Extract contexts
        for context in root.findall(".//xbrli:context", self.NAMESPACES):
            context_id = context.get("id")
            period = context.find("xbrli:period", self.NAMESPACES)

            if period is not None:
                instant = period.find("xbrli:instant", self.NAMESPACES)
                start = period.find("xbrli:startDate", self.NAMESPACES)
                end = period.find("xbrli:endDate", self.NAMESPACES)

                data["contexts"][context_id] = {
                    "instant": instant.text if instant is not None else None,
                    "start": start.text if start is not None else None,
                    "end": end.text if end is not None else None,
                }

        # Extract facts (all elements in root that aren't contexts or units)
        for element in root:
            # Skip metadata elements
            if element.tag.endswith("context") or element.tag.endswith("unit"):
                continue

            try:
                # Get fact details
                name = element.tag.split("}")[-1]  # Remove namespace
                context_ref = element.get("contextRef")
                value_text = element.text

                if value_text:
                    value = self._parse_numeric_value(value_text)
                    statement_type = self._infer_statement_type(name)

                    if statement_type and value is not None:
                        data["statements"][statement_type].append({
                            "name": self._clean_fact_name(name),
                            "value": value,
                            "context": context_ref,
                        })

            except Exception:
                continue

        return data

    def _parse_numeric_value(self, value_text: str) -> Optional[Decimal]:
        """
        Parse a numeric value from text.

        Args:
            value_text: Text representation of a number

        Returns:
            Decimal value or None
        """
        try:
            # Remove common formatting
            cleaned = value_text.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()

            # Handle empty or non-numeric
            if not cleaned or cleaned == "-":
                return None

            return Decimal(cleaned)

        except (ValueError, TypeError):
            return None

    def _clean_fact_name(self, name: str) -> str:
        """
        Clean a fact name to a readable format.

        Args:
            name: Raw fact name from XBRL

        Returns:
            Cleaned, readable name
        """
        # Remove namespace prefix
        if ":" in name:
            name = name.split(":")[-1]

        # Split camel case with spaces
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)

        return name

    def _infer_statement_type(self, fact_name: str) -> Optional[str]:
        """
        Infer which statement a fact belongs to based on its name.

        Args:
            fact_name: Name of the XBRL fact

        Returns:
            Statement type code ('IS', 'BS', 'CF') or None
        """
        lower_name = fact_name.lower()

        # Income Statement indicators
        if any(
            keyword in lower_name
            for keyword in [
                "revenue",
                "income",
                "expense",
                "earnings",
                "profit",
                "loss",
                "sales",
                "cost",
            ]
        ):
            return "IS"

        # Balance Sheet indicators
        if any(
            keyword in lower_name
            for keyword in [
                "asset",
                "liability",
                "equity",
                "stockholder",
                "shareholder",
                "debt",
                "payable",
                "receivable",
            ]
        ):
            return "BS"

        # Cash Flow indicators
        if any(
            keyword in lower_name
            for keyword in ["cash", "cashflow", "financing", "investing", "operating"]
        ):
            return "CF"

        return None

    def extract_financial_statements(
        self, parsed_data: Dict, period_end_date: str
    ) -> Dict[str, List[Dict]]:
        """
        Extract and organize financial statements from parsed data.

        Args:
            parsed_data: Output from parse_filing_*
            period_end_date: Period end date to filter contexts

        Returns:
            Dictionary with organized statements
        """
        statements = {"IS": [], "BS": [], "CF": []}

        # Find the context matching the period
        target_context = None
        for context_id, context_data in parsed_data.get("contexts", {}).items():
            if context_data.get("end") == period_end_date or context_data.get("instant") == period_end_date:
                target_context = context_id
                break

        if not target_context:
            print(f"Warning: No context found for period {period_end_date}")
            return statements

        # Filter facts by context and organize by statement
        for stmt_type in ["IS", "BS", "CF"]:
            facts = parsed_data.get("statements", {}).get(stmt_type, [])
            filtered_facts = [
                {"line_item_name": f["name"], "value": float(f["value"])}
                for f in facts
                if f["context"] == target_context and f["value"] is not None
            ]

            # Add display order
            for i, fact in enumerate(filtered_facts):
                fact["display_order"] = i + 1

            statements[stmt_type] = filtered_facts

        return statements


# Global instance
xbrl_parser = XBRLParser()
