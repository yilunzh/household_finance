"""
Transaction routes: list, create, update, delete.
"""
from datetime import datetime
from flask import render_template, request, jsonify

from extensions import db
from models import Transaction, Settlement, ExpenseType, BudgetRule, AutoCategoryRule
from decorators import household_required
from household_context import get_current_household_id, get_current_household_members
from utils import calculate_reconciliation, build_split_rules_lookup
from services.transaction_service import TransactionService
from blueprints.transactions import transactions_bp


@transactions_bp.route('/')
@household_required
def index():
    """Main page with transaction form and list."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    # Get month from query params, default to current month
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    # Get all transactions for the month (FILTERED BY HOUSEHOLD)
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()

    # Calculate quick summary with split rules
    split_rules_lookup = build_split_rules_lookup(household_id)
    if transactions:
        summary = calculate_reconciliation(transactions, household_members, None, split_rules_lookup)
    else:
        summary = None

    # Build split info dict for template display: {expense_type_id: (member1_pct, member2_pct)}
    split_display_info = {}
    for key, rule in split_rules_lookup.items():
        split_display_info[key] = (rule.member1_percent, rule.member2_percent)

    # Get list of available months for dropdown (FILTERED BY HOUSEHOLD)
    existing_months = db.session.query(Transaction.month_year).distinct().filter(
        Transaction.household_id == household_id
    ).order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in existing_months]

    # Always ensure current month is in list
    current_month_str = datetime.now().strftime('%Y-%m')
    if current_month_str not in months:
        months.insert(0, current_month_str)

    # If viewing a month not in list (manually typed URL), add it
    if month not in months:
        # Insert in correct chronological position
        months.append(month)
        months.sort(reverse=True)

    # Check if month is settled (HOUSEHOLD-SCOPED)
    is_settled = Settlement.is_month_settled(household_id, month)

    # Get expense types for the dropdown
    expense_types = ExpenseType.query.filter_by(
        household_id=household_id,
        is_active=True
    ).order_by(ExpenseType.name).all()

    # Get budget rules for auto-defaulting split category
    budget_rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()
    budget_rules_json = [r.to_dict() for r in budget_rules]

    # Build combined merchant suggestions from rules + past transactions
    rule_keywords = [r.keyword for r in AutoCategoryRule.query.filter_by(
        household_id=household_id).all()]
    txn_merchants = [m[0] for m in db.session.query(Transaction.merchant).filter(
        Transaction.household_id == household_id).distinct().all() if m[0]]
    # Deduplicate case-insensitively, prefer rule keyword casing
    seen = {}
    for m in rule_keywords:
        seen[m.lower()] = m
    for m in txn_merchants:
        if m.lower() not in seen:
            seen[m.lower()] = m
    merchant_suggestions = sorted(seen.values(), key=str.lower)

    return render_template(
        'index.html',
        transactions=transactions,
        current_month=month,
        months=months,
        summary=summary,
        is_settled=is_settled,
        household_members=household_members,
        expense_types=expense_types,
        budget_rules_json=budget_rules_json,
        split_display_info=split_display_info,
        merchant_suggestions=merchant_suggestions
    )


@transactions_bp.route('/transaction', methods=['POST'])
@household_required
def add_transaction():
    """Add a new transaction."""
    try:
        household_id = get_current_household_id()
        data = request.json

        transaction = TransactionService.create_transaction(household_id, data)

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

    except TransactionService.ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@transactions_bp.route('/transaction/<int:transaction_id>', methods=['PUT'])
@household_required
def update_transaction(transaction_id):
    """Update an existing transaction."""
    try:
        household_id = get_current_household_id()
        data = request.json

        transaction = TransactionService.update_transaction(
            household_id, transaction_id, data
        )

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

    except TransactionService.ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@transactions_bp.route('/transaction/<int:transaction_id>', methods=['DELETE'])
@household_required
def delete_transaction(transaction_id):
    """Delete a transaction."""
    try:
        household_id = get_current_household_id()

        TransactionService.delete_transaction(household_id, transaction_id)

        return jsonify({
            'success': True
        })

    except TransactionService.ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
