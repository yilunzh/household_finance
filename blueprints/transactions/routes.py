"""
Transaction routes: list, create, update, delete.
"""
from datetime import datetime
from decimal import Decimal
from flask import render_template, request, jsonify
from flask_login import current_user

from extensions import db
from models import Transaction, Settlement, HouseholdMember, ExpenseType, BudgetRule
from decorators import household_required
from household_context import get_current_household_id, get_current_household_members
from utils import calculate_reconciliation, get_exchange_rate, build_split_rules_lookup
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
        split_display_info=split_display_info
    )


@transactions_bp.route('/transaction', methods=['POST'])
@household_required
def add_transaction():
    """Add a new transaction."""
    try:
        household_id = get_current_household_id()
        data = request.json

        # Parse date
        txn_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Get exchange rate if needed
        amount = Decimal(str(data['amount']))
        currency = data['currency']

        if currency == 'CAD':
            rate = get_exchange_rate('CAD', 'USD', txn_date)
            amount_in_usd = amount * Decimal(str(rate))
        else:
            amount_in_usd = amount

        # Check if month is settled (locked) - HOUSEHOLD-SCOPED
        month_year_to_check = txn_date.strftime('%Y-%m')
        if Settlement.is_month_settled(household_id, month_year_to_check):
            return jsonify({
                'success': False,
                'error': f'Cannot add transaction to settled month {month_year_to_check}. This month is locked.'
            }), 403

        # Validate paid_by_user_id belongs to this household
        paid_by_user_id = int(data['paid_by'])  # Now expects user_id instead of 'ME'/'WIFE'
        member = HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=paid_by_user_id
        ).first()

        if not member:
            return jsonify({
                'success': False,
                'error': 'Invalid user selected. User is not a member of this household.'
            }), 400

        # Handle expense_type_id (optional)
        expense_type_id = data.get('expense_type_id')
        if expense_type_id:
            expense_type_id = int(expense_type_id)
            # Verify it belongs to this household
            expense_type = ExpenseType.query.filter_by(
                id=expense_type_id,
                household_id=household_id,
                is_active=True
            ).first()
            if not expense_type:
                expense_type_id = None

        # Create transaction (NEW SCHEMA)
        transaction = Transaction(
            household_id=household_id,
            date=txn_date,
            merchant=data['merchant'],
            amount=amount,
            currency=currency,
            amount_in_usd=amount_in_usd,
            paid_by_user_id=paid_by_user_id,
            category=data['category'],
            expense_type_id=expense_type_id,
            notes=data.get('notes', ''),
            month_year=txn_date.strftime('%Y-%m')
        )

        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

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

        # Verify ownership: transaction must belong to current household
        transaction = Transaction.query.filter_by(
            id=transaction_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        # Check if OLD month is settled (HOUSEHOLD-SCOPED)
        if Settlement.is_month_settled(household_id, transaction.month_year):
            return jsonify({
                'success': False,
                'error': f'Cannot edit transaction in settled month {transaction.month_year}. This month is locked.'
            }), 403

        # Also check if NEW month (if date changed) is settled
        if 'date' in data:
            new_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            new_month_year = new_date.strftime('%Y-%m')
            if new_month_year != transaction.month_year and Settlement.is_month_settled(household_id, new_month_year):
                return jsonify({
                    'success': False,
                    'error': f'Cannot move transaction to settled month {new_month_year}. That month is locked.'
                }), 403

        # Update fields
        if 'date' in data:
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            transaction.month_year = transaction.date.strftime('%Y-%m')

        if 'merchant' in data:
            transaction.merchant = data['merchant']

        if 'amount' in data or 'currency' in data:
            amount = Decimal(str(data.get('amount', transaction.amount)))
            currency = data.get('currency', transaction.currency)

            transaction.amount = amount
            transaction.currency = currency

            # Recalculate amount_in_usd
            if currency == 'CAD':
                rate = get_exchange_rate('CAD', 'USD', transaction.date)
                transaction.amount_in_usd = amount * Decimal(str(rate))
            else:
                transaction.amount_in_usd = amount

        if 'paid_by' in data:
            # Validate user belongs to household
            paid_by_user_id = int(data['paid_by'])
            member = HouseholdMember.query.filter_by(
                household_id=household_id,
                user_id=paid_by_user_id
            ).first()

            if not member:
                return jsonify({
                    'success': False,
                    'error': 'Invalid user selected.'
                }), 400

            transaction.paid_by_user_id = paid_by_user_id

        if 'category' in data:
            transaction.category = data['category']

        if 'expense_type_id' in data:
            expense_type_id = data['expense_type_id']
            if expense_type_id:
                expense_type_id = int(expense_type_id)
                # Verify it belongs to this household
                expense_type = ExpenseType.query.filter_by(
                    id=expense_type_id,
                    household_id=household_id,
                    is_active=True
                ).first()
                transaction.expense_type_id = expense_type_id if expense_type else None
            else:
                transaction.expense_type_id = None

        if 'notes' in data:
            transaction.notes = data['notes']

        db.session.commit()

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

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

        # Verify ownership: transaction must belong to current household
        transaction = Transaction.query.filter_by(
            id=transaction_id,
            household_id=household_id
        ).first_or_404()

        # Check if month is settled (HOUSEHOLD-SCOPED)
        if Settlement.is_month_settled(household_id, transaction.month_year):
            return jsonify({
                'success': False,
                'error': f'Cannot delete transaction in settled month {transaction.month_year}. This month is locked.'
            }), 403

        db.session.delete(transaction)
        db.session.commit()

        return jsonify({
            'success': True
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
