"""
Reconciliation API routes for mobile app.

Endpoints:
- GET /api/v1/reconciliation/<month> - Get reconciliation summary for a month
- POST /api/v1/settlement - Mark a month as settled
- DELETE /api/v1/settlement/<month> - Unsettle a month
"""
from datetime import date

from flask import request, jsonify, g

from extensions import db
from models import Transaction, Settlement, HouseholdMember, BudgetRule
from api_decorators import jwt_required, api_household_required
from utils import calculate_reconciliation, build_split_rules_lookup
from budget_utils import calculate_budget_status
from blueprints.api_v1 import api_v1_bp


def _get_household_budget_status(household_id, month, transactions):
    """Calculate budget status for all budget rules in a household.

    Returns:
        List of budget status dicts, one per rule. Empty list if no rules.
    """
    budget_rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    if not budget_rules:
        return []

    budget_statuses = []
    for rule in budget_rules:
        status = calculate_budget_status(rule, month, transactions)
        # Add rule info to status
        status['rule_id'] = rule.id
        status['giver_user_id'] = rule.giver_user_id
        status['receiver_user_id'] = rule.receiver_user_id
        status['giver_display_name'] = rule.get_giver_display_name()
        status['receiver_display_name'] = rule.get_receiver_display_name()
        # Convert Decimals to floats for JSON serialization
        status['budget_amount'] = float(status['budget_amount'])
        status['spent_amount'] = float(status['spent_amount'])
        status['giver_reimbursement'] = float(status['giver_reimbursement'])
        status['remaining'] = float(status['remaining'])
        status['carryover_from_previous'] = float(status['carryover_from_previous'])
        status['net_balance'] = float(status['net_balance'])
        # Remove transactions from status (already returned separately)
        status.pop('transactions', None)
        budget_statuses.append(status)

    return budget_statuses


@api_v1_bp.route('/reconciliation/<month>', methods=['GET'])
@jwt_required
@api_household_required
def api_get_reconciliation(month):
    """Get reconciliation summary for a month.

    Path Parameters:
        month: Month in YYYY-MM format

    Returns:
        {
            "month": "2024-01",
            "is_settled": false,
            "settlement": null,
            "transactions": [...],
            "summary": {
                "user_payments": {...},
                "user_shares": {...},
                "balances": {...},
                "settlement_message": "Alice owes Bob $50.00"
            },
            "budget_status": {...}
        }
    """
    household_id = g.household_id

    # Get transactions for the month
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).order_by(Transaction.date.desc()).all()

    # Get household members
    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    # Get split rules
    split_rules_lookup = build_split_rules_lookup(household_id)

    # Check if month is settled
    settlement = Settlement.get_settlement(household_id, month)
    is_settled = settlement is not None

    # Calculate budget status for all budget rules
    budget_statuses = _get_household_budget_status(household_id, month, transactions)

    recon_result = calculate_reconciliation(
        transactions=transactions,
        household_members=members,
        budget_data=budget_statuses if budget_statuses else None,
        split_rules_lookup=split_rules_lookup
    )

    # Calculate total spent from user_payments
    total_spent = sum(recon_result['user_payments'].values())

    # Build response
    response = {
        'month': month,
        'is_settled': is_settled,
        'settlement': settlement.to_dict() if settlement else None,
        'transactions': [txn.to_dict() for txn in transactions],
        'summary': {
            'user_payments': recon_result['user_payments'],
            'user_shares': recon_result['user_shares'],
            'balances': recon_result['user_balances'],
            'settlement_message': recon_result['settlement'],
            'total_spent': total_spent,
            'breakdown': recon_result['breakdown'],
            'member_names': recon_result['member_names']
        }
    }

    # Include budget status if available
    if budget_statuses:
        response['budget_status'] = budget_statuses

    return jsonify(response)


@api_v1_bp.route('/settlement', methods=['POST'])
@jwt_required
@api_household_required
def api_create_settlement():
    """Mark a month as settled.

    Request body:
        {
            "month": "2024-01"
        }

    Returns:
        {"settlement": {...}}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    month = data.get('month')
    if not month:
        return jsonify({'error': 'Month is required'}), 400

    household_id = g.household_id

    # Check if already settled
    if Settlement.is_month_settled(household_id, month):
        return jsonify({'error': 'Month is already settled'}), 400

    # Get transactions and calculate settlement
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).all()

    if not transactions:
        return jsonify({'error': 'No transactions found for this month'}), 400

    # Get household members
    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    if len(members) < 2:
        return jsonify({'error': 'At least 2 household members required for settlement'}), 400

    # Get split rules
    split_rules_lookup = build_split_rules_lookup(household_id)

    # Calculate budget status for all budget rules
    budget_statuses = _get_household_budget_status(household_id, month, transactions)

    recon_result = calculate_reconciliation(
        transactions=transactions,
        household_members=members,
        budget_data=budget_statuses if budget_statuses else None,
        split_rules_lookup=split_rules_lookup
    )

    # Determine who owes whom
    balances = recon_result['user_balances']
    settlement_message = recon_result['settlement']

    # Find the member who owes and who is owed
    from_user_id = None
    to_user_id = None
    settlement_amount = 0

    for user_id, balance in balances.items():
        if balance < 0:
            from_user_id = user_id
            settlement_amount = abs(balance)
        elif balance > 0:
            to_user_id = user_id

    # Handle edge case where balance is zero
    if from_user_id is None or to_user_id is None:
        # Both users balanced, pick arbitrarily
        user_ids = list(balances.keys())
        from_user_id = user_ids[0]
        to_user_id = user_ids[1] if len(user_ids) > 1 else user_ids[0]
        settlement_amount = 0

    try:
        settlement = Settlement(
            household_id=household_id,
            month_year=month,
            settled_date=date.today(),
            settlement_amount=settlement_amount,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            settlement_message=settlement_message
        )

        db.session.add(settlement)
        db.session.commit()

        return jsonify({
            'settlement': settlement.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create settlement'}), 500


@api_v1_bp.route('/settlement/<month>', methods=['DELETE'])
@jwt_required
@api_household_required
def api_delete_settlement(month):
    """Unsettle a month (remove settlement record).

    Path Parameters:
        month: Month in YYYY-MM format

    Returns:
        {"success": true}
    """
    household_id = g.household_id

    settlement = Settlement.get_settlement(household_id, month)

    if not settlement:
        return jsonify({'error': 'Month is not settled'}), 404

    try:
        db.session.delete(settlement)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to remove settlement'}), 500
