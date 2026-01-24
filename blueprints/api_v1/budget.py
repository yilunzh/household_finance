"""
Budget and Split Rules API routes for mobile app.

Endpoints:
- GET /api/v1/budget-rules - List budget rules
- POST /api/v1/budget-rules - Create budget rule
- PUT /api/v1/budget-rules/<id> - Update budget rule
- DELETE /api/v1/budget-rules/<id> - Delete budget rule
- POST /api/v1/split-rules - Create split rule
- PUT /api/v1/split-rules/<id> - Update split rule
- DELETE /api/v1/split-rules/<id> - Delete split rule
"""
from decimal import Decimal
from flask import request, jsonify, g

from extensions import db
from models import (
    BudgetRule, BudgetRuleExpenseType, ExpenseType,
    SplitRule, SplitRuleExpenseType, HouseholdMember
)
from api_decorators import jwt_required, api_household_required
from blueprints.api_v1 import api_v1_bp


def _cleanup_empty_split_rules(household_id, exclude_rule_id=None):
    """Remove split rules that have no expense types and are not default."""
    rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_default=False,
        is_active=True
    ).all()

    for rule in rules:
        if rule.id != exclude_rule_id and not rule.expense_types:
            rule.is_active = False


# ============================================================================
# Budget Rules API Routes
# ============================================================================

@api_v1_bp.route('/budget-rules', methods=['GET'])
@jwt_required
@api_household_required
def api_get_budget_rules():
    """Get all budget rules for the current household.

    Returns:
        {
            "budget_rules": [
                {
                    "id": 1,
                    "giver_user_id": 1,
                    "giver_name": "Alice",
                    "receiver_user_id": 2,
                    "receiver_name": "Bob",
                    "monthly_amount": 500.00,
                    "expense_type_ids": [1, 2],
                    "expense_type_names": ["Grocery", "Dining"],
                    "is_active": true
                },
                ...
            ]
        }
    """
    household_id = g.household_id

    rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    return jsonify({
        'budget_rules': [r.to_dict() for r in rules]
    })


@api_v1_bp.route('/budget-rules', methods=['POST'])
@jwt_required
@api_household_required
def api_create_budget_rule():
    """Create a new budget rule.

    Request body:
        {
            "giver_user_id": 1,
            "receiver_user_id": 2,
            "monthly_amount": 500.00,
            "expense_type_ids": [1, 2]
        }

    Returns:
        {"budget_rule": {...}}
    """
    household_id = g.household_id
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    giver_user_id = data.get('giver_user_id')
    receiver_user_id = data.get('receiver_user_id')
    monthly_amount = data.get('monthly_amount')
    expense_type_ids = data.get('expense_type_ids', [])

    # Validation
    if not giver_user_id or not receiver_user_id:
        return jsonify({'error': 'Giver and receiver are required'}), 400

    if giver_user_id == receiver_user_id:
        return jsonify({'error': 'Giver and receiver must be different'}), 400

    if not monthly_amount or float(monthly_amount) <= 0:
        return jsonify({'error': 'Monthly amount must be positive'}), 400

    if not expense_type_ids:
        return jsonify({'error': 'At least one expense type is required'}), 400

    # Verify both users are members of household
    for user_id in [giver_user_id, receiver_user_id]:
        member = HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=user_id
        ).first()
        if not member:
            return jsonify({'error': 'Invalid user selected'}), 400

    # Validate expense types belong to this household
    for et_id in expense_type_ids:
        expense_type = ExpenseType.query.filter_by(
            id=et_id,
            household_id=household_id,
            is_active=True
        ).first()
        if not expense_type:
            return jsonify({'error': 'Invalid expense type selected'}), 400

    # Check if expense types are already used in other active budget rules
    for et_id in expense_type_ids:
        existing_usage = BudgetRuleExpenseType.query.filter_by(
            expense_type_id=et_id
        ).join(BudgetRule).filter(
            BudgetRule.household_id == household_id,
            BudgetRule.is_active.is_(True)
        ).first()

        if existing_usage:
            expense_type = ExpenseType.query.get(et_id)
            return jsonify({
                'error': f'Expense type "{expense_type.name}" is already used in another budget rule'
            }), 400

    try:
        # Create budget rule
        budget_rule = BudgetRule(
            household_id=household_id,
            giver_user_id=giver_user_id,
            receiver_user_id=receiver_user_id,
            monthly_amount=Decimal(str(monthly_amount))
        )

        db.session.add(budget_rule)
        db.session.flush()  # Get the ID

        # Add expense type associations
        for et_id in expense_type_ids:
            assoc = BudgetRuleExpenseType(
                budget_rule_id=budget_rule.id,
                expense_type_id=et_id
            )
            db.session.add(assoc)

        db.session.commit()

        return jsonify({'budget_rule': budget_rule.to_dict()}), 201

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to create budget rule'}), 500


@api_v1_bp.route('/budget-rules/<int:rule_id>', methods=['PUT'])
@jwt_required
@api_household_required
def api_update_budget_rule(rule_id):
    """Update a budget rule.

    Request body:
        {
            "monthly_amount": 600.00,
            "expense_type_ids": [1, 2, 3]
        }

    Returns:
        {"budget_rule": {...}}
    """
    household_id = g.household_id

    budget_rule = BudgetRule.query.filter_by(
        id=rule_id,
        household_id=household_id,
        is_active=True
    ).first()

    if not budget_rule:
        return jsonify({'error': 'Budget rule not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    try:
        if 'monthly_amount' in data:
            amount = float(data['monthly_amount'])
            if amount <= 0:
                return jsonify({'error': 'Monthly amount must be positive'}), 400
            budget_rule.monthly_amount = Decimal(str(amount))

        if 'expense_type_ids' in data:
            expense_type_ids = data['expense_type_ids']

            if not expense_type_ids:
                return jsonify({'error': 'At least one expense type is required'}), 400

            # Validate expense types belong to this household
            for et_id in expense_type_ids:
                expense_type = ExpenseType.query.filter_by(
                    id=et_id,
                    household_id=household_id,
                    is_active=True
                ).first()
                if not expense_type:
                    return jsonify({'error': 'Invalid expense type selected'}), 400

            # Check for conflicts with other budget rules
            for et_id in expense_type_ids:
                existing_usage = BudgetRuleExpenseType.query.filter_by(
                    expense_type_id=et_id
                ).join(BudgetRule).filter(
                    BudgetRule.household_id == household_id,
                    BudgetRule.is_active.is_(True),
                    BudgetRule.id != rule_id
                ).first()

                if existing_usage:
                    expense_type = ExpenseType.query.get(et_id)
                    return jsonify({
                        'error': f'Expense type "{expense_type.name}" is already used in another budget rule'
                    }), 400

            # Remove existing associations
            BudgetRuleExpenseType.query.filter_by(budget_rule_id=rule_id).delete()

            # Add new associations
            for et_id in expense_type_ids:
                assoc = BudgetRuleExpenseType(
                    budget_rule_id=rule_id,
                    expense_type_id=et_id
                )
                db.session.add(assoc)

        db.session.commit()

        return jsonify({'budget_rule': budget_rule.to_dict()})

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to update budget rule'}), 500


@api_v1_bp.route('/budget-rules/<int:rule_id>', methods=['DELETE'])
@jwt_required
@api_household_required
def api_delete_budget_rule(rule_id):
    """Deactivate a budget rule (soft delete).

    Returns:
        {"success": true}
    """
    household_id = g.household_id

    budget_rule = BudgetRule.query.filter_by(
        id=rule_id,
        household_id=household_id,
        is_active=True
    ).first()

    if not budget_rule:
        return jsonify({'error': 'Budget rule not found'}), 404

    try:
        budget_rule.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete budget rule'}), 500


# ============================================================================
# Split Rules API Routes
# ============================================================================

@api_v1_bp.route('/split-rules', methods=['POST'])
@jwt_required
@api_household_required
def api_create_split_rule():
    """Create a new split rule.

    Request body:
        {
            "member1_percent": 60,
            "member2_percent": 40,
            "is_default": false,
            "expense_type_ids": [1, 2]
        }

    Returns:
        {"split_rule": {...}}
    """
    household_id = g.household_id
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    member1_percent = int(data.get('member1_percent', 50))
    member2_percent = int(data.get('member2_percent', 50))
    is_default = bool(data.get('is_default', False))
    expense_type_ids = data.get('expense_type_ids', [])

    # Validation
    if member1_percent + member2_percent != 100:
        return jsonify({'error': 'Percentages must sum to 100'}), 400

    if member1_percent < 0 or member2_percent < 0:
        return jsonify({'error': 'Percentages cannot be negative'}), 400

    # If it's a default rule, check no other default exists
    if is_default:
        existing_default = SplitRule.query.filter_by(
            household_id=household_id,
            is_default=True,
            is_active=True
        ).first()
        if existing_default:
            return jsonify({'error': 'A default split rule already exists'}), 400
    else:
        # Non-default rules require expense types
        if not expense_type_ids:
            return jsonify({'error': 'Select at least one expense category, or mark as default'}), 400

    # Validate expense types belong to this household
    for et_id in expense_type_ids:
        expense_type = ExpenseType.query.filter_by(
            id=et_id,
            household_id=household_id,
            is_active=True
        ).first()
        if not expense_type:
            return jsonify({'error': 'Invalid expense type selected'}), 400

    # Get household members for response
    household_members = HouseholdMember.query.filter_by(household_id=household_id).all()

    try:
        # Create the rule
        rule = SplitRule(
            household_id=household_id,
            member1_percent=member1_percent,
            member2_percent=member2_percent,
            is_default=is_default
        )
        db.session.add(rule)
        db.session.flush()  # Get the ID

        # Handle expense type associations
        for et_id in expense_type_ids:
            # Remove from other rules
            SplitRuleExpenseType.query.filter_by(
                expense_type_id=et_id
            ).filter(
                SplitRuleExpenseType.split_rule_id != rule.id
            ).delete(synchronize_session='fetch')

            # Add to this rule
            assoc = SplitRuleExpenseType(
                split_rule_id=rule.id,
                expense_type_id=et_id
            )
            db.session.add(assoc)

        db.session.commit()

        # Auto-delete any rules that are now empty
        _cleanup_empty_split_rules(household_id, exclude_rule_id=rule.id)
        db.session.commit()

        return jsonify({'split_rule': rule.to_dict(household_members)}), 201

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to create split rule'}), 500


@api_v1_bp.route('/split-rules/<int:rule_id>', methods=['PUT'])
@jwt_required
@api_household_required
def api_update_split_rule(rule_id):
    """Update a split rule.

    Request body:
        {
            "member1_percent": 70,
            "member2_percent": 30,
            "expense_type_ids": [1, 2, 3]
        }

    Returns:
        {"split_rule": {...}}
    """
    household_id = g.household_id

    split_rule = SplitRule.query.filter_by(
        id=rule_id,
        household_id=household_id,
        is_active=True
    ).first()

    if not split_rule:
        return jsonify({'error': 'Split rule not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    # Get household members for response
    household_members = HouseholdMember.query.filter_by(household_id=household_id).all()

    try:
        # Update percentages
        if 'member1_percent' in data and 'member2_percent' in data:
            member1_percent = int(data['member1_percent'])
            member2_percent = int(data['member2_percent'])

            if member1_percent + member2_percent != 100:
                return jsonify({'error': 'Percentages must sum to 100'}), 400

            if member1_percent < 0 or member2_percent < 0:
                return jsonify({'error': 'Percentages cannot be negative'}), 400

            split_rule.member1_percent = member1_percent
            split_rule.member2_percent = member2_percent

        # Update expense types
        if 'expense_type_ids' in data:
            expense_type_ids = data['expense_type_ids']

            # Non-default rules need at least one expense type
            if not split_rule.is_default and not expense_type_ids:
                return jsonify({'error': 'Non-default rules require at least one expense category'}), 400

            # Validate expense types belong to this household
            for et_id in expense_type_ids:
                expense_type = ExpenseType.query.filter_by(
                    id=et_id,
                    household_id=household_id,
                    is_active=True
                ).first()
                if not expense_type:
                    return jsonify({'error': 'Invalid expense type selected'}), 400

            # Remove existing associations for this rule
            SplitRuleExpenseType.query.filter_by(split_rule_id=rule_id).delete()

            # Add new associations, removing from other rules
            for et_id in expense_type_ids:
                # Remove from other rules
                SplitRuleExpenseType.query.filter_by(
                    expense_type_id=et_id
                ).filter(
                    SplitRuleExpenseType.split_rule_id != rule_id
                ).delete(synchronize_session='fetch')

                # Add to this rule
                assoc = SplitRuleExpenseType(
                    split_rule_id=rule_id,
                    expense_type_id=et_id
                )
                db.session.add(assoc)

        db.session.commit()

        # Auto-delete any rules that are now empty
        _cleanup_empty_split_rules(household_id, exclude_rule_id=rule_id)
        db.session.commit()

        return jsonify({'split_rule': split_rule.to_dict(household_members)})

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to update split rule'}), 500


@api_v1_bp.route('/split-rules/<int:rule_id>', methods=['DELETE'])
@jwt_required
@api_household_required
def api_delete_split_rule(rule_id):
    """Deactivate a split rule (soft delete).

    Returns:
        {"success": true}
    """
    household_id = g.household_id

    split_rule = SplitRule.query.filter_by(
        id=rule_id,
        household_id=household_id,
        is_active=True
    ).first()

    if not split_rule:
        return jsonify({'error': 'Split rule not found'}), 404

    try:
        split_rule.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete split rule'}), 500
