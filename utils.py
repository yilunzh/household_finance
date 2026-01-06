"""
Utility functions for household expense tracker.
"""
import requests
from datetime import datetime, date
from decimal import Decimal

# Cache for exchange rates to minimize API calls
_rate_cache = {}


def get_exchange_rate(from_currency, to_currency, date_str):
    """
    Get exchange rate for a specific date, with caching.

    Args:
        from_currency (str): Source currency code (e.g., 'USD')
        to_currency (str): Target currency code (e.g., 'CAD')
        date_str (str or date): Date in YYYY-MM-DD format or date object

    Returns:
        float: Exchange rate
    """
    # Convert date object to string if needed
    if isinstance(date_str, date):
        date_str = date_str.strftime('%Y-%m-%d')

    # If currencies are the same, rate is 1.0
    if from_currency == to_currency:
        return 1.0

    # Check cache first
    cache_key = f"{from_currency}_{to_currency}_{date_str}"
    if cache_key in _rate_cache:
        return _rate_cache[cache_key]

    try:
        # Call frankfurter.app API for historical rate
        url = f"https://api.frankfurter.app/{date_str}"
        params = {'from': from_currency, 'to': to_currency}
        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            rate = response.json()['rates'][to_currency]
            _rate_cache[cache_key] = rate
            return rate
        else:
            # If historical rate not available, try current rate
            return get_current_exchange_rate(from_currency, to_currency)

    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        # Fallback to current rate
        return get_current_exchange_rate(from_currency, to_currency)


def get_current_exchange_rate(from_currency, to_currency):
    """
    Get current exchange rate.

    Args:
        from_currency (str): Source currency code
        to_currency (str): Target currency code

    Returns:
        float: Current exchange rate or 1.4 as fallback
    """
    if from_currency == to_currency:
        return 1.0

    cache_key = f"{from_currency}_{to_currency}_current"

    try:
        url = "https://api.frankfurter.app/latest"
        params = {'from': from_currency, 'to': to_currency}
        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            rate = response.json()['rates'][to_currency]
            _rate_cache[cache_key] = rate
            return rate

    except Exception as e:
        print(f"Error fetching current exchange rate: {e}")

    # Fallback rate (approximate USD to CAD)
    return 1.4 if from_currency == 'USD' and to_currency == 'CAD' else 1.0


def calculate_reconciliation(transactions):
    """
    Calculate who owes what based on transactions.

    Args:
        transactions (list): List of Transaction model instances

    Returns:
        dict: Summary containing:
            - me_paid: Total amount I paid (in USD)
            - wife_paid: Total amount wife paid (in USD)
            - me_share: My share of expenses (in USD)
            - wife_share: Wife's share of expenses (in USD)
            - me_balance: My balance (positive = owed to me, negative = I owe)
            - wife_balance: Wife's balance
            - settlement: Human-readable settlement message
            - breakdown: Category breakdown
    """
    me_paid = Decimal('0.00')
    wife_paid = Decimal('0.00')
    me_share = Decimal('0.00')
    wife_share = Decimal('0.00')

    # Track category totals
    category_totals = {}

    for txn in transactions:
        amount_usd = Decimal(str(txn.amount_in_usd))

        # Track who paid
        if txn.paid_by == 'ME':
            me_paid += amount_usd
        else:
            wife_paid += amount_usd

        # Calculate each person's share based on category
        if txn.category == 'SHARED':
            me_share += amount_usd * Decimal('0.5')
            wife_share += amount_usd * Decimal('0.5')
        elif txn.category == 'I_PAY_FOR_WIFE':
            wife_share += amount_usd
        elif txn.category == 'WIFE_PAYS_FOR_ME':
            me_share += amount_usd
        elif txn.category == 'PERSONAL_ME':
            me_share += amount_usd
        elif txn.category == 'PERSONAL_WIFE':
            wife_share += amount_usd

        # Track category totals
        category = txn.category
        if category not in category_totals:
            category_totals[category] = {
                'count': 0,
                'total': Decimal('0.00')
            }
        category_totals[category]['count'] += 1
        category_totals[category]['total'] += amount_usd

    # Calculate net balances
    me_balance = me_paid - me_share
    wife_balance = wife_paid - wife_share

    # Format settlement message
    settlement = format_settlement(me_balance, wife_balance)

    # Format breakdown
    breakdown = []
    for category, data in category_totals.items():
        from models import Transaction
        breakdown.append({
            'category': category,
            'category_name': Transaction.get_category_display_name(category),
            'count': data['count'],
            'total': float(data['total'])
        })

    # Sort breakdown by total descending
    breakdown.sort(key=lambda x: x['total'], reverse=True)

    return {
        'me_paid': float(me_paid),
        'wife_paid': float(wife_paid),
        'me_share': float(me_share),
        'wife_share': float(wife_share),
        'me_balance': float(me_balance),
        'wife_balance': float(wife_balance),
        'settlement': settlement,
        'breakdown': breakdown
    }


def format_settlement(me_balance, wife_balance):
    """
    Format the settlement message in a human-readable way.

    Args:
        me_balance (Decimal): My balance
        wife_balance (Decimal): Wife's balance

    Returns:
        str: Settlement message
    """
    # Account for floating point precision
    threshold = Decimal('0.01')

    if me_balance > threshold:
        return f"Pi owes Bibi ${abs(float(me_balance)):.2f}"
    elif wife_balance > threshold:
        return f"Bibi owes Pi ${abs(float(wife_balance)):.2f}"
    else:
        return "All settled up!"
