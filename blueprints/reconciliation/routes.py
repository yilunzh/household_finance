"""
Reconciliation routes: settlement, reconciliation view, export.
"""
import csv
from io import StringIO
from datetime import datetime
from flask import render_template, request, jsonify, Response

from extensions import db
from models import Transaction, Settlement, BudgetRule, SplitRule
from decorators import household_required
from household_context import get_current_household_id, get_current_household_members
from utils import calculate_reconciliation, build_split_rules_lookup
from budget_utils import calculate_budget_status
from services.reconciliation_service import ReconciliationService
from blueprints.reconciliation import reconciliation_bp


@reconciliation_bp.route('/settlement', methods=['POST'])
@household_required
def mark_month_settled():
    """Mark a month as settled and record the settlement snapshot."""
    try:
        household_id = get_current_household_id()
        household_members = get_current_household_members()
        data = request.json
        month_year = data['month_year']

        settlement = ReconciliationService.create_settlement(
            household_id, household_members, month_year
        )

        return jsonify({'success': True, 'settlement': settlement.to_dict()})

    except ReconciliationService.SettlementError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@reconciliation_bp.route('/settlement/<month_year>', methods=['DELETE'])
@household_required
def unsettle_month(month_year):
    """Remove settlement record to unlock a month for editing."""
    try:
        household_id = get_current_household_id()

        ReconciliationService.remove_settlement(household_id, month_year)

        return jsonify({
            'success': True,
            'message': f'Month {month_year} has been unsettled and is now unlocked.'
        })

    except ReconciliationService.SettlementError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@reconciliation_bp.route('/reconciliation')
@reconciliation_bp.route('/reconciliation/<month>')
@household_required
def reconciliation(month=None):
    """Show monthly reconciliation summary."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    if month is None:
        month = datetime.now().strftime('%Y-%m')

    # Get all transactions for the month (FILTERED BY HOUSEHOLD)
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).all()

    # Get budget rules and calculate budget data for reconciliation
    budget_rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    budget_data = []
    for rule in budget_rules:
        status = calculate_budget_status(rule, month, transactions)
        budget_data.append({
            'rule': rule,
            'giver_name': rule.get_giver_display_name(),
            'giver_user_id': rule.giver_user_id,
            'receiver_name': rule.get_receiver_display_name(),
            'receiver_user_id': rule.receiver_user_id,
            'monthly_amount': rule.monthly_amount,
            'expense_type_names': rule.get_expense_type_names(),
            'status': status,
        })

    # Get split rules for custom SHARED splits
    split_rules_lookup = build_split_rules_lookup(household_id)

    # Calculate reconciliation with household members, budget data, and split rules
    summary = calculate_reconciliation(transactions, household_members, budget_data, split_rules_lookup)

    # Get list of available months (FILTERED BY HOUSEHOLD)
    all_months = db.session.query(Transaction.month_year).distinct().filter(
        Transaction.household_id == household_id
    ).order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in all_months]

    # Always ensure current month is in list (matches transactions page behavior)
    current_month_str = datetime.now().strftime('%Y-%m')
    if current_month_str not in months:
        months.insert(0, current_month_str)

    # If viewing a month not in list (e.g. manually typed URL), add it
    if month not in months:
        months.append(month)
        months.sort(reverse=True)

    # Check if month is settled (HOUSEHOLD-SCOPED)
    settlement = Settlement.get_settlement(household_id, month)

    # Get split rules for display
    split_rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()
    split_rules_data = [r.to_dict(household_members) for r in split_rules]

    # Build split info dict for template display: {expense_type_id: (member1_pct, member2_pct)}
    split_display_info = {}
    for key, rule in split_rules_lookup.items():
        split_display_info[key] = (rule.member1_percent, rule.member2_percent)

    return render_template(
        'reconciliation.html',
        summary=summary,
        month=month,
        months=months,
        transactions=transactions,
        settlement=settlement,
        household_members=household_members,
        budget_data=budget_data,
        split_rules=split_rules_data,
        split_display_info=split_display_info
    )


@reconciliation_bp.route('/export/<month>')
@household_required
def export_csv(month):
    """Export transactions for a month as CSV."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    # Get transactions for this household (FILTERED BY HOUSEHOLD)
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).order_by(Transaction.date).all()

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Date', 'Merchant', 'Amount', 'Currency', 'Amount (USD)',
        'Paid By', 'Category', 'Notes'
    ])

    # Write transactions
    for txn in transactions:
        writer.writerow([
            txn.date.strftime('%Y-%m-%d'),
            txn.merchant,
            f'{float(txn.amount):.2f}',
            txn.currency,
            f'{float(txn.amount_in_usd):.2f}',
            txn.get_paid_by_display_name(),
            Transaction.get_category_display_name(txn.category, household_members),
            txn.notes or ''
        ])

    # Add summary (with household members)
    summary = calculate_reconciliation(transactions, household_members)
    writer.writerow([])
    writer.writerow(['SUMMARY'])

    # Dynamic member names in summary
    for member in household_members:
        user_id = member.user_id
        if user_id in summary.get('user_payments', {}):
            paid_amount = summary['user_payments'][user_id]
            writer.writerow([f'{member.display_name} paid', f'${paid_amount:.2f}'])

    writer.writerow([])
    writer.writerow(['Settlement', summary['settlement']])

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=expenses_{month}.csv'
        }
    )
