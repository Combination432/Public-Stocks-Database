"""
Data validation for financial statements.

Implements validation rules like the balance sheet equation.
"""
from decimal import Decimal
from typing import Dict, List, Optional


class DataValidator:
    """
    Validate financial statement data.

    Implements checks for data quality and integrity.
    """

    def __init__(self, tolerance: float = 0.0001):
        """
        Initialize the data validator.

        Args:
            tolerance: Tolerance for numerical comparisons (default: 0.01%)
        """
        self.tolerance = tolerance
        self.errors = []
        self.warnings = []

    def validate_balance_sheet(self, balance_sheet_data: List[Dict]) -> bool:
        """
        Validate the balance sheet equation: Assets = Liabilities + Equity

        Args:
            balance_sheet_data: List of balance sheet line items

        Returns:
            True if valid, False otherwise
        """
        # Extract key values
        total_assets = self._find_value(balance_sheet_data, ["Total Assets", "Assets"])
        total_liabilities = self._find_value(
            balance_sheet_data, ["Total Liabilities", "Liabilities"]
        )
        total_equity = self._find_value(
            balance_sheet_data,
            [
                "Total Equity",
                "Stockholders Equity",
                "Shareholders Equity",
                "Total Stockholders Equity",
                "Total Shareholders Equity",
            ],
        )

        if total_assets is None:
            self.warnings.append("Balance Sheet: Total Assets not found")
            return True  # Don't fail validation, just warn

        if total_liabilities is None or total_equity is None:
            self.warnings.append(
                "Balance Sheet: Total Liabilities or Equity not found"
            )
            return True

        # Check equation: Assets = Liabilities + Equity
        liabilities_plus_equity = total_liabilities + total_equity
        difference = abs(total_assets - liabilities_plus_equity)

        # Calculate relative error
        if total_assets != 0:
            relative_error = difference / abs(total_assets)
        else:
            relative_error = 0

        if relative_error > self.tolerance:
            self.errors.append(
                f"Balance Sheet equation violated: Assets ({total_assets}) != "
                f"Liabilities ({total_liabilities}) + Equity ({total_equity}). "
                f"Difference: {difference} ({relative_error * 100:.4f}%)"
            )
            return False

        return True

    def validate_cash_flow(self, cash_flow_data: List[Dict]) -> bool:
        """
        Validate cash flow statement reconciliation.

        Args:
            cash_flow_data: List of cash flow line items

        Returns:
            True if valid, False otherwise
        """
        # Extract cash flow components
        operating_cf = self._find_value(
            cash_flow_data,
            [
                "Net Cash Provided by Operating Activities",
                "Operating Activities",
                "Cash from Operating Activities",
            ],
        )
        investing_cf = self._find_value(
            cash_flow_data,
            [
                "Net Cash Used in Investing Activities",
                "Investing Activities",
                "Cash from Investing Activities",
            ],
        )
        financing_cf = self._find_value(
            cash_flow_data,
            [
                "Net Cash Provided by Financing Activities",
                "Financing Activities",
                "Cash from Financing Activities",
            ],
        )

        if None in [operating_cf, investing_cf, financing_cf]:
            self.warnings.append(
                "Cash Flow: Not all activity sections found (Operating, Investing, Financing)"
            )
            return True

        # Check if there's a net change in cash
        net_change = self._find_value(
            cash_flow_data,
            [
                "Net Change in Cash",
                "Net Increase in Cash",
                "Net Decrease in Cash",
                "Change in Cash",
            ],
        )

        if net_change is not None:
            calculated_change = operating_cf + investing_cf + financing_cf
            difference = abs(net_change - calculated_change)

            if abs(net_change) > 0:
                relative_error = difference / abs(net_change)
            else:
                relative_error = 0

            if relative_error > self.tolerance:
                self.warnings.append(
                    f"Cash Flow reconciliation mismatch: Reported change ({net_change}) != "
                    f"Sum of activities ({calculated_change}). Difference: {difference}"
                )

        return True

    def validate_income_statement(self, income_statement_data: List[Dict]) -> bool:
        """
        Validate income statement data.

        Args:
            income_statement_data: List of income statement line items

        Returns:
            True if valid, False otherwise
        """
        # Basic sanity checks
        revenue = self._find_value(
            income_statement_data,
            ["Revenue", "Total Revenue", "Net Revenue", "Sales", "Total Net Revenues"],
        )

        if revenue is not None and revenue < 0:
            self.warnings.append(
                f"Income Statement: Revenue is negative ({revenue}). This is unusual."
            )

        # Check for gross profit calculation if available
        cost_of_revenue = self._find_value(
            income_statement_data, ["Cost of Revenue", "Cost of Sales", "Cost of Goods Sold"]
        )
        gross_profit = self._find_value(
            income_statement_data, ["Gross Profit", "Gross Margin"]
        )

        if all(v is not None for v in [revenue, cost_of_revenue, gross_profit]):
            calculated_gp = revenue - cost_of_revenue
            difference = abs(gross_profit - calculated_gp)

            if abs(calculated_gp) > 0:
                relative_error = difference / abs(calculated_gp)
            else:
                relative_error = 0

            if relative_error > self.tolerance:
                self.warnings.append(
                    f"Income Statement: Gross Profit ({gross_profit}) != "
                    f"Revenue ({revenue}) - Cost ({cost_of_revenue}). Difference: {difference}"
                )

        return True

    def validate_all_statements(self, statements: Dict[str, List[Dict]]) -> Dict:
        """
        Validate all three financial statements.

        Args:
            statements: Dictionary with 'IS', 'BS', 'CF' keys

        Returns:
            Dictionary with validation results
        """
        self.errors = []
        self.warnings = []

        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        # Validate each statement
        if "BS" in statements and statements["BS"]:
            if not self.validate_balance_sheet(statements["BS"]):
                results["valid"] = False

        if "CF" in statements and statements["CF"]:
            self.validate_cash_flow(statements["CF"])

        if "IS" in statements and statements["IS"]:
            self.validate_income_statement(statements["IS"])

        results["errors"] = self.errors.copy()
        results["warnings"] = self.warnings.copy()

        return results

    def _find_value(
        self, data: List[Dict], possible_names: List[str]
    ) -> Optional[Decimal]:
        """
        Find a value in data by checking multiple possible line item names.

        Args:
            data: List of line items
            possible_names: List of possible names to search for

        Returns:
            The value if found, None otherwise
        """
        for item in data:
            line_name = item.get("line_item_name", "")
            for name in possible_names:
                if name.lower() in line_name.lower():
                    value = item.get("value")
                    if value is not None:
                        return Decimal(str(value))

        return None

    def get_validation_summary(self) -> str:
        """Get a summary of validation errors and warnings."""
        summary = []

        if self.errors:
            summary.append(f"ERRORS ({len(self.errors)}):")
            for error in self.errors:
                summary.append(f"  - {error}")

        if self.warnings:
            summary.append(f"WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                summary.append(f"  - {warning}")

        if not self.errors and not self.warnings:
            summary.append("All validations passed!")

        return "\n".join(summary)


# Global instance
data_validator = DataValidator()
