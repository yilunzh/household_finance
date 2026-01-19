"""
Budget page route.
"""
from datetime import datetime
from flask import render_template

from extensions import db
from models import Transaction, BudgetRule
from decorators import household_required
from household_context import get_current_household_id
from budget_utils import calculate_budget_status, get_yearly_cumulative
from blueprints.budget import budget_bp


@budget_bp.route('/budget')
@budget_bp.route('/budget/<month>')
@household_required
def budget_page(month=None):
    """Budget tracking page."""
    household_id = get_current_household_id()

    # Get month from URL or default to current month
    if not month:
        month = datetime.now().strftime('%Y-%m')

    # Get available months (same as index page)
    existing_months = db.session.query(Transaction.month_year).distinct().filter(
        Transaction.household_id == household_id
    ).order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in existing_months]

    # Ensure current month is in list
    current_month_str = datetime.now().strftime('%Y-%m')
    if current_month_str not in months:
        months.insert(0, current_month_str)

    if month not in months:
        months.append(month)
        months.sort(reverse=True)

    # Get all transactions for the month
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).all()

    # Get budget rules
    budget_rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    # Calculate status for each budget rule
    budget_data = []
    current_year = month.split('-')[0]

    for rule in budget_rules:
        status = calculate_budget_status(rule, month, transactions)
        yearly_cumulative = get_yearly_cumulative(rule.id, current_year)

        budget_data.append({
            'rule': rule,
            'giver_name': rule.get_giver_display_name(),
            'giver_user_id': rule.giver_user_id,
            'receiver_name': rule.get_receiver_display_name(),
            'receiver_user_id': rule.receiver_user_id,
            'monthly_amount': rule.monthly_amount,
            'expense_type_names': rule.get_expense_type_names(),
            'status': status,
            'yearly_cumulative': yearly_cumulative,
        })

    return render_template(
        'budget/index.html',
        current_month=month,
        months=months,
        budget_rules=budget_rules,
        budget_data=budget_data,
        current_year=current_year
    )
