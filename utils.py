"""
Utility functions for household expense tracker.
"""
import requests
from datetime import date
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


def get_split_for_expense_type(household_id, expense_type_id, split_rules_lookup=None):
    """
    Get the split percentages for an expense type.

    Args:
        household_id (int): The household ID
        expense_type_id (int or None): The expense type ID (can be None)
        split_rules_lookup (dict, optional): Pre-loaded lookup dict {expense_type_id: SplitRule}
                                             If None, will query database

    Returns:
        tuple: (member1_percent, member2_percent) as Decimal (0-1 range, e.g., 0.5 for 50%)
               Member1 is always the owner, Member2 is the other member.
    """
    default_split = (Decimal('0.5'), Decimal('0.5'))

    if split_rules_lookup is not None:
        # Use pre-loaded lookup
        # First, check if there's a specific rule for this expense type
        if expense_type_id in split_rules_lookup:
            rule = split_rules_lookup[expense_type_id]
            return (
                Decimal(str(rule.member1_percent)) / 100,
                Decimal(str(rule.member2_percent)) / 100
            )
        # Fall back to default rule (None key) if it exists
        if None in split_rules_lookup:
            rule = split_rules_lookup[None]
            return (
                Decimal(str(rule.member1_percent)) / 100,
                Decimal(str(rule.member2_percent)) / 100
            )
        return default_split

    # Query database for split rule
    from models import SplitRule, SplitRuleExpenseType

    # First, try to find a rule that covers this specific expense type
    if expense_type_id:
        rule_link = SplitRuleExpenseType.query.join(SplitRule).filter(
            SplitRule.household_id == household_id,
            SplitRule.is_active.is_(True),
            SplitRuleExpenseType.expense_type_id == expense_type_id
        ).first()

        if rule_link:
            return (
                Decimal(str(rule_link.split_rule.member1_percent)) / 100,
                Decimal(str(rule_link.split_rule.member2_percent)) / 100
            )

    # Fall back to default rule (is_default=True)
    default_rule = SplitRule.query.filter_by(
        household_id=household_id,
        is_default=True,
        is_active=True
    ).first()

    if default_rule:
        return (
            Decimal(str(default_rule.member1_percent)) / 100,
            Decimal(str(default_rule.member2_percent)) / 100
        )

    return default_split


def build_split_rules_lookup(household_id):
    """
    Build a lookup dictionary for split rules.

    Args:
        household_id (int): The household ID

    Returns:
        dict: {expense_type_id: SplitRule} where None key = default rule
    """
    from models import SplitRule

    lookup = {}

    # Get all active split rules for this household
    rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    for rule in rules:
        if rule.is_default:
            # Default rule (applies when no specific rule matches)
            lookup[None] = rule
        else:
            # Map each expense type to this rule
            for expense_link in rule.expense_types:
                lookup[expense_link.expense_type_id] = rule

    return lookup


def calculate_reconciliation(transactions, household_members, budget_data=None, split_rules_lookup=None):
    """
    Calculate who owes what based on transactions (NEW: dynamic household members).

    Args:
        transactions (list): List of Transaction model instances
        household_members (list): List of HouseholdMember instances
        budget_data (list, optional): List of budget data dicts with 'giver_user_id', 'receiver_user_id',
                                      and 'status' containing 'giver_reimbursement'
        split_rules_lookup (dict, optional): Pre-loaded lookup dict {expense_type_id: SplitRule}
                                             for custom SHARED splits. If None, will use 50/50.

    Returns:
        dict: Summary containing:
            - user_payments: Dict of {user_id: amount_paid}
            - user_shares: Dict of {user_id: amount_owed}
            - user_balances: Dict of {user_id: balance} (positive = owed to them, negative = they owe)
            - settlement: Human-readable settlement message
            - breakdown: Category breakdown
            - member_names: Dict of {user_id: display_name}
            - budget_reimbursements: List of budget reimbursement details
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
            # Determine member ordering: owner is always member1
            owner = next((m for m in household_members if m.role == 'owner'), household_members[0])
            other = next((m for m in household_members if m.user_id != owner.user_id), household_members[1])
            user1_id = owner.user_id  # Owner
            user2_id = other.user_id  # Other member

            if txn.category == 'SHARED':
                # Use custom split if available, otherwise 50/50
                if split_rules_lookup is not None:
                    m1_pct, m2_pct = get_split_for_expense_type(
                        None, txn.expense_type_id, split_rules_lookup
                    )
                else:
                    m1_pct, m2_pct = Decimal('0.5'), Decimal('0.5')
                user_shares[user1_id] += amount_usd * m1_pct
                user_shares[user2_id] += amount_usd * m2_pct
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

    # Process budget reimbursements
    # When giver pays for budget items, receiver owes giver that amount
    budget_reimbursements = []
    if budget_data:
        for bd in budget_data:
            giver_id = bd.get('giver_user_id')
            receiver_id = bd.get('receiver_user_id')
            status = bd.get('status', {})
            reimbursement = float(status.get('giver_reimbursement', 0))

            if reimbursement > 0.01 and giver_id in user_balances and receiver_id in user_balances:
                # Giver paid for budget items, so receiver owes giver
                # This increases giver's balance (owed to them)
                # And decreases receiver's balance (they owe more)
                user_balances[giver_id] += reimbursement
                user_balances[receiver_id] -= reimbursement

                budget_reimbursements.append({
                    'giver_name': member_names.get(giver_id, 'Giver'),
                    'receiver_name': member_names.get(receiver_id, 'Receiver'),
                    'amount': reimbursement,
                    'expense_types': bd.get('expense_type_names', [])
                })

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
        'member_names': member_names,
        'budget_reimbursements': budget_reimbursements
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


def calculate_user_stats(user_id):
    """
    Calculate YTD statistics for a user across all households.

    Args:
        user_id (int): The user's ID

    Returns:
        dict: Statistics including total spent, reimbursements, monthly trends
    """
    from datetime import datetime
    from models import Transaction, Settlement, HouseholdMember, Household

    current_year = datetime.utcnow().year
    ytd_start = f"{current_year}-01"

    # Get all household memberships for user
    memberships = HouseholdMember.query.filter_by(user_id=user_id).all()
    household_ids = [m.household_id for m in memberships]

    if not household_ids:
        return {
            'ytd_total_paid': 0,
            'monthly_average': 0,
            'total_owed_to_user': 0,
            'settled_owed_to_user': 0,
            'active_owed_to_user': 0,
            'total_owed_by_user': 0,
            'settled_owed_by_user': 0,
            'active_owed_by_user': 0,
            'household_breakdown': [],
            'monthly_trend': []
        }

    # Calculate YTD total paid by user across all households
    ytd_transactions = Transaction.query.filter(
        Transaction.paid_by_user_id == user_id,
        Transaction.household_id.in_(household_ids),
        Transaction.month_year >= ytd_start
    ).all()

    ytd_total_paid = sum(float(t.amount_in_usd) for t in ytd_transactions)

    # Calculate monthly breakdown for trends
    monthly_data = {}
    for t in ytd_transactions:
        month = t.month_year
        if month not in monthly_data:
            monthly_data[month] = 0
        monthly_data[month] += float(t.amount_in_usd)

    # Sort by month and create trend list
    sorted_months = sorted(monthly_data.keys())
    monthly_trend = [
        {'month': m[5:], 'amount': monthly_data[m]}  # e.g., "01", "02"
        for m in sorted_months
    ]

    # Calculate monthly average
    months_with_data = len(monthly_data) if monthly_data else 1
    monthly_average = ytd_total_paid / months_with_data

    # Calculate reimbursements from settlements
    # Settled amounts owed TO user (user was owed money)
    settled_to_user = Settlement.query.filter(
        Settlement.to_user_id == user_id,
        Settlement.household_id.in_(household_ids),
        Settlement.month_year >= ytd_start
    ).all()
    settled_owed_to_user = sum(float(s.settlement_amount) for s in settled_to_user)

    # Settled amounts owed BY user (user owed money)
    settled_by_user = Settlement.query.filter(
        Settlement.from_user_id == user_id,
        Settlement.household_id.in_(household_ids),
        Settlement.month_year >= ytd_start
    ).all()
    settled_owed_by_user = sum(float(s.settlement_amount) for s in settled_by_user)

    # For active (unsettled) reimbursements, we need to calculate from transactions
    active_owed_to_user = Decimal('0')
    active_owed_by_user = Decimal('0')

    # Calculate active balances for unsettled months (per household)
    for membership in memberships:
        household_id = membership.household_id
        household_members = HouseholdMember.query.filter_by(household_id=household_id).all()

        if len(household_members) < 2:
            continue

        # Get settled months for THIS household only
        household_settled_months = set(s.month_year for s in Settlement.query.filter(
            Settlement.household_id == household_id,
            Settlement.month_year >= ytd_start
        ).all())

        # Get unsettled transactions for this household
        if household_settled_months:
            unsettled_transactions = Transaction.query.filter(
                Transaction.household_id == household_id,
                Transaction.month_year >= ytd_start,
                ~Transaction.month_year.in_(household_settled_months)
            ).all()
        else:
            # No settled months - all transactions are unsettled
            unsettled_transactions = Transaction.query.filter(
                Transaction.household_id == household_id,
                Transaction.month_year >= ytd_start
            ).all()

        if not unsettled_transactions:
            continue

        # Build split rules lookup
        split_rules_lookup = build_split_rules_lookup(household_id)

        # Calculate reconciliation
        summary = calculate_reconciliation(unsettled_transactions, household_members, None, split_rules_lookup)

        # Find this user's balance in user_balances dict
        user_balances = summary.get('user_balances', {})
        if user_id in user_balances:
            balance = Decimal(str(user_balances[user_id]))
            if balance > 0:
                # User is owed money
                active_owed_to_user += balance
            else:
                # User owes money
                active_owed_by_user += abs(balance)

    # Per-household breakdown
    household_breakdown = []
    for membership in memberships:
        household = Household.query.get(membership.household_id)
        household_paid = sum(
            float(t.amount_in_usd) for t in ytd_transactions
            if t.household_id == membership.household_id
        )
        if household_paid > 0:
            household_breakdown.append({
                'household_name': household.name,
                'total_paid': household_paid
            })

    return {
        'ytd_total_paid': round(ytd_total_paid, 2),
        'monthly_average': round(monthly_average, 2),
        'total_owed_to_user': round(float(settled_owed_to_user) + float(active_owed_to_user), 2),
        'settled_owed_to_user': round(settled_owed_to_user, 2),
        'active_owed_to_user': round(float(active_owed_to_user), 2),
        'total_owed_by_user': round(float(settled_owed_by_user) + float(active_owed_by_user), 2),
        'settled_owed_by_user': round(settled_owed_by_user, 2),
        'active_owed_by_user': round(float(active_owed_by_user), 2),
        'household_breakdown': household_breakdown,
        'monthly_trend': monthly_trend
    }
