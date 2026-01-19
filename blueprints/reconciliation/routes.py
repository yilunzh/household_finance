"""
Reconciliation routes: settlement, reconciliation view, export.
"""
import csv
from io import StringIO
from datetime import datetime
from decimal import Decimal
from flask import render_template, request, jsonify, Response

from extensions import db
from models import Transaction, Settlement, BudgetRule, BudgetSnapshot, SplitRule
from decorators import household_required
from household_context import get_current_household_id, get_current_household_members
from utils import calculate_reconciliation, build_split_rules_lookup
from budget_utils import calculate_budget_status, create_or_update_budget_snapshot
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

        # Validation: Check if already settled (HOUSEHOLD-SCOPED)
        if Settlement.is_month_settled(household_id, month_year):
            return jsonify({'success': False, 'error': 'This month has already been settled.'}), 400

        # Validation: Must have transactions (HOUSEHOLD-SCOPED)
        transactions = Transaction.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).all()

        if not transactions:
            return jsonify({'success': False, 'error': 'Cannot settle a month with no transactions.'}), 400

        # Get split rules for custom SHARED splits
        split_rules_lookup = build_split_rules_lookup(household_id)

        # Calculate reconciliation with household members and split rules
        summary = calculate_reconciliation(transactions, household_members, None, split_rules_lookup)

        # Extract balances (NEW: use dynamic user balances)
        # For now, assume 2-person household (will be enhanced in Phase 4)
        user_balances = summary.get('user_balances', {})

        if len(user_balances) != 2:
            return jsonify({
                'success': False,
                'error': 'Settlement currently only supports 2-person households.'
            }), 400

        # Get the two users and their balances
        user_ids = list(user_balances.keys())
        user1_id = user_ids[0]
        user2_id = user_ids[1]
        user1_balance = Decimal(str(user_balances[user1_id]))
        user2_balance = Decimal(str(user_balances[user2_id]))

        # Determine direction of debt (NEW SCHEMA)
        if user1_balance > Decimal('0.01'):  # User2 owes User1
            from_user_id, to_user_id, settlement_amount = user2_id, user1_id, user1_balance
        elif user2_balance > Decimal('0.01'):  # User1 owes User2
            from_user_id, to_user_id, settlement_amount = user1_id, user2_id, user2_balance
        else:  # All settled up
            from_user_id, to_user_id, settlement_amount = user1_id, user2_id, Decimal('0.00')

        # Create settlement record (NEW SCHEMA)
        settlement = Settlement(
            household_id=household_id,
            month_year=month_year,
            settled_date=datetime.now().date(),
            settlement_amount=settlement_amount,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            settlement_message=summary['settlement']
        )

        db.session.add(settlement)

        # Create budget snapshots for all active budget rules
        budget_rules = BudgetRule.query.filter_by(
            household_id=household_id,
            is_active=True
        ).all()

        for budget_rule in budget_rules:
            create_or_update_budget_snapshot(budget_rule, month_year, finalize=True)

        db.session.commit()

        return jsonify({'success': True, 'settlement': settlement.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@reconciliation_bp.route('/settlement/<month_year>', methods=['DELETE'])
@household_required
def unsettle_month(month_year):
    """Remove settlement record to unlock a month for editing."""
    try:
        household_id = get_current_household_id()

        # Get settlement for this household (HOUSEHOLD-SCOPED)
        settlement = Settlement.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).first()

        if not settlement:
            return jsonify({
                'success': False,
                'error': 'This month is not settled.'
            }), 404

        db.session.delete(settlement)

        # Unfinalize budget snapshots for this month
        budget_rules = BudgetRule.query.filter_by(
            household_id=household_id,
            is_active=True
        ).all()

        for budget_rule in budget_rules:
            snapshot = BudgetSnapshot.query.filter_by(
                budget_rule_id=budget_rule.id,
                month_year=month_year
            ).first()
            if snapshot:
                snapshot.is_finalized = False

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Month {month_year} has been unsettled and is now unlocked.'
        })

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
