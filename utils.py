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


def calculate_reconciliation(transactions, household_members):
    """
    Calculate who owes what based on transactions (NEW: dynamic household members).

    Args:
        transactions (list): List of Transaction model instances
        household_members (list): List of HouseholdMember instances

    Returns:
        dict: Summary containing:
            - user_payments: Dict of {user_id: amount_paid}
            - user_shares: Dict of {user_id: amount_owed}
            - user_balances: Dict of {user_id: balance} (positive = owed to them, negative = they owe)
            - settlement: Human-readable settlement message
            - breakdown: Category breakdown
            - member_names: Dict of {user_id: display_name}
    """
    # Initialize tracking dictionaries for each household member
    user_payments = {}  # How much each user paid
    user_shares = {}    # How much each user owes
    member_names = {}   # User ID to display name mapping

    for member in household_members:
        user_id = member.user_id
        user_payments[user_id] = Decimal('0.00')
        user_shares[user_id] = Decimal('0.00')
        member_names[user_id] = member.display_name

    # Track category totals
    category_totals = {}

    # Process transactions
    for txn in transactions:
        amount_usd = Decimal(str(txn.amount_in_usd))
        paid_by_user_id = txn.paid_by_user_id

        # Track who paid
        if paid_by_user_id in user_payments:
            user_payments[paid_by_user_id] += amount_usd

        # Calculate each person's share based on category
        # NOTE: For 2-person households only (will be enhanced in Phase 4 for 3+ members)
        if len(household_members) == 2:
            member_ids = list(user_payments.keys())
            user1_id = member_ids[0]
            user2_id = member_ids[1]

            if txn.category == 'SHARED':
                # 50/50 split
                user_shares[user1_id] += amount_usd * Decimal('0.5')
                user_shares[user2_id] += amount_usd * Decimal('0.5')
            elif txn.category == 'I_PAY_FOR_WIFE':
                # Member 1 pays for Member 2 (Member 2 owes 100%)
                user_shares[user2_id] += amount_usd
            elif txn.category == 'WIFE_PAYS_FOR_ME':
                # Member 2 pays for Member 1 (Member 1 owes 100%)
                user_shares[user1_id] += amount_usd
            elif txn.category == 'PERSONAL_ME':
                # Personal expense for Member 1
                user_shares[user1_id] += amount_usd
            elif txn.category == 'PERSONAL_WIFE':
                # Personal expense for Member 2
                user_shares[user2_id] += amount_usd

        # Track category totals
        category = txn.category
        if category not in category_totals:
            category_totals[category] = {
                'count': 0,
                'total': Decimal('0.00')
            }
        category_totals[category]['count'] += 1
        category_totals[category]['total'] += amount_usd

    # Calculate net balances for each user
    user_balances = {}
    for user_id in user_payments:
        balance = user_payments[user_id] - user_shares[user_id]
        user_balances[user_id] = float(balance)

    # Format settlement message (for 2-person households)
    settlement = format_settlement_dynamic(user_balances, member_names)

    # Format breakdown
    breakdown = []
    for category, data in category_totals.items():
        from models import Transaction
        breakdown.append({
            'category': category,
            'category_name': Transaction.get_category_display_name(category, household_members),
            'count': data['count'],
            'total': float(data['total'])
        })

    # Sort breakdown by total descending
    breakdown.sort(key=lambda x: x['total'], reverse=True)

    return {
        'user_payments': {uid: float(amt) for uid, amt in user_payments.items()},
        'user_shares': {uid: float(amt) for uid, amt in user_shares.items()},
        'user_balances': user_balances,
        'settlement': settlement,
        'breakdown': breakdown,
        'member_names': member_names
    }


def format_settlement_dynamic(user_balances, member_names):
    """
    Format the settlement message with dynamic member names.

    Args:
        user_balances (dict): Dict of {user_id: balance}
        member_names (dict): Dict of {user_id: display_name}

    Returns:
        str: Settlement message
    """
    threshold = 0.01

    # For 2-person households
    if len(user_balances) == 2:
        user_ids = list(user_balances.keys())
        user1_id = user_ids[0]
        user2_id = user_ids[1]

        balance1 = user_balances[user1_id]
        balance2 = user_balances[user2_id]

        name1 = member_names.get(user1_id, "Member 1")
        name2 = member_names.get(user2_id, "Member 2")

        if balance1 > threshold:
            # User1 is owed money, User2 owes User1
            return f"{name2} owes {name1} ${abs(balance1):.2f}"
        elif balance2 > threshold:
            # User2 is owed money, User1 owes User2
            return f"{name1} owes {name2} ${abs(balance2):.2f}"
        else:
            return "All settled up!"

    # Fallback for non-2-person households
    return "Settlement calculation available for 2-person households only"


def format_settlement(me_balance, wife_balance):
    """
    LEGACY: Format the settlement message in a human-readable way.
    Kept for backward compatibility. Use format_settlement_dynamic instead.

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
