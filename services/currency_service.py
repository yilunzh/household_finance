"""
Currency conversion service.

Handles exchange rate lookups and currency conversion.
"""
from decimal import Decimal
from utils import get_exchange_rate, get_current_exchange_rate


class CurrencyService:
    """Service for currency conversion operations."""

    @staticmethod
    def convert_to_usd(amount, currency, txn_date):
        """
        Convert an amount to USD.

        Args:
            amount (Decimal or float): The amount to convert
            currency (str): The currency code (e.g., 'USD', 'CAD')
            txn_date (date or str): The transaction date

        Returns:
            Decimal: The amount in USD
        """
        amount = Decimal(str(amount))

        if currency == 'USD':
            return amount

        if currency == 'CAD':
            rate = get_exchange_rate('CAD', 'USD', txn_date)
            return amount * Decimal(str(rate))

        # Default: assume 1:1 for unknown currencies
        return amount

    @staticmethod
    def get_rate(from_currency, to_currency, date_str=None):
        """
        Get exchange rate between currencies.

        Args:
            from_currency (str): Source currency code
            to_currency (str): Target currency code
            date_str (str or date, optional): Date for historical rate

        Returns:
            float: Exchange rate
        """
        if date_str:
            return get_exchange_rate(from_currency, to_currency, date_str)
        return get_current_exchange_rate(from_currency, to_currency)
