"""Budget calculation utilities for household expense tracker."""

from decimal import Decimal
from models import db, Transaction, BudgetRule, BudgetSnapshot


def calculate_budget_status(budget_rule, month_year, transactions=None):
    """
    Calculate budget status for a specific month.

    Args:
        budget_rule: BudgetRule instance
        month_year: String in format 'YYYY-MM'
        transactions: Optional list of transactions (fetched if not provided)

    Returns:
        dict with budget status:
        {
            'budget_amount': Decimal,
            'spent_amount': Decimal,
            'giver_reimbursement': Decimal,
            'remaining': Decimal,
            'percent_used': float,
            'is_over_budget': bool,
            'carryover_from_previous': Decimal,
            'net_balance': Decimal,  # positive = surplus, negative = deficit
        }
    """
    household_id = budget_rule.household_id

    # Get expense type IDs for this rule
    expense_type_ids = budget_rule.get_expense_type_ids()

    if not expense_type_ids:
        return {
            'budget_amount': budget_rule.monthly_amount,
            'spent_amount': Decimal('0.00'),
            'giver_reimbursement': Decimal('0.00'),
            'remaining': budget_rule.monthly_amount,
            'percent_used': 0.0,
            'is_over_budget': False,
            'carryover_from_previous': Decimal('0.00'),
            'net_balance': budget_rule.monthly_amount,
        }

    # Fetch transactions if not provided
    if transactions is None:
        transactions = Transaction.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).all()

    # Filter transactions to only those with matching expense types
    budget_transactions = [
        txn for txn in transactions
        if txn.expense_type_id in expense_type_ids
    ]

    # Calculate totals
    spent_amount = Decimal('0.00')
    giver_reimbursement = Decimal('0.00')

    for txn in budget_transactions:
        amount = Decimal(str(txn.amount_in_usd))
        spent_amount += amount

        # If the giver paid for this item, they should be reimbursed
        if txn.paid_by_user_id == budget_rule.giver_user_id:
            giver_reimbursement += amount

    budget_amount = budget_rule.monthly_amount
    remaining = budget_amount - spent_amount
    percent_used = float(spent_amount / budget_amount * 100) if budget_amount > 0 else 0.0
    is_over_budget = spent_amount > budget_amount

    # Get carryover from previous month
    carryover = get_carryover_from_previous(budget_rule.id, month_year)

    # Net balance = budget - spent + carryover
    # Positive = surplus (saved money), Negative = deficit (overspent)
    net_balance = budget_amount - spent_amount + carryover

    return {
        'budget_amount': budget_amount,
        'spent_amount': spent_amount,
        'giver_reimbursement': giver_reimbursement,
        'remaining': remaining,
        'percent_used': min(percent_used, 100.0),  # Cap at 100 for display
        'is_over_budget': is_over_budget,
        'carryover_from_previous': carryover,
        'net_balance': net_balance,
        'transactions': budget_transactions,
    }


def get_carryover_from_previous(budget_rule_id, month_year):
    """
    Get the carryover balance from the previous month.

    For January, this returns 0 (yearly reset).
    For other months, it returns the net_balance from the previous month's snapshot.
    """
    year, month = month_year.split('-')
    year = int(year)
    month = int(month)

    # January reset: no carryover
    if month == 1:
        return Decimal('0.00')

    # Calculate previous month
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    prev_month_year = f"{prev_year:04d}-{prev_month:02d}"

    # Look for finalized snapshot
    snapshot = BudgetSnapshot.query.filter_by(
        budget_rule_id=budget_rule_id,
        month_year=prev_month_year,
        is_finalized=True
    ).first()

    if snapshot:
        return Decimal(str(snapshot.net_balance))

    # If no finalized snapshot, calculate dynamically
    budget_rule = BudgetRule.query.get(budget_rule_id)
    if budget_rule:
        prev_status = calculate_budget_status(budget_rule, prev_month_year)
        return prev_status['net_balance']

    return Decimal('0.00')


def get_yearly_cumulative(budget_rule_id, year):
    """
    Calculate cumulative surplus/deficit for the year.

    Sums net_balance from all finalized snapshots in the year.
    """
    snapshots = BudgetSnapshot.query.filter(
        BudgetSnapshot.budget_rule_id == budget_rule_id,
        BudgetSnapshot.month_year.like(f'{year}-%'),
        BudgetSnapshot.is_finalized.is_(True)
    ).all()

    if not snapshots:
        return Decimal('0.00')

    return sum(Decimal(str(s.net_balance)) for s in snapshots)


def create_or_update_budget_snapshot(budget_rule, month_year, finalize=False):
    """
    Create or update a budget snapshot for the month.

    Args:
        budget_rule: BudgetRule instance
        month_year: String in format 'YYYY-MM'
        finalize: Whether to mark as finalized (locked)

    Returns:
        BudgetSnapshot instance
    """
    status = calculate_budget_status(budget_rule, month_year)

    snapshot = BudgetSnapshot.query.filter_by(
        budget_rule_id=budget_rule.id,
        month_year=month_year
    ).first()

    if not snapshot:
        snapshot = BudgetSnapshot(
            budget_rule_id=budget_rule.id,
            month_year=month_year,
            budget_amount=status['budget_amount'],
            spent_amount=status['spent_amount'],
            giver_reimbursement=status['giver_reimbursement'],
            carryover_from_previous=status['carryover_from_previous'],
            net_balance=status['net_balance'],
            is_finalized=finalize
        )
        db.session.add(snapshot)
    else:
        snapshot.budget_amount = status['budget_amount']
        snapshot.spent_amount = status['spent_amount']
        snapshot.giver_reimbursement = status['giver_reimbursement']
        snapshot.carryover_from_previous = status['carryover_from_previous']
        snapshot.net_balance = status['net_balance']
        if finalize:
            snapshot.is_finalized = True

    db.session.commit()
    return snapshot


def get_budget_transactions(household_id, budget_rule, month_year):
    """
    Get all transactions for a budget rule in a specific month.
    """
    expense_type_ids = budget_rule.get_expense_type_ids()

    if not expense_type_ids:
        return []

    return Transaction.query.filter(
        Transaction.household_id == household_id,
        Transaction.month_year == month_year,
        Transaction.expense_type_id.in_(expense_type_ids)
    ).order_by(Transaction.date.desc()).all()
