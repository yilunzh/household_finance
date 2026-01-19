"""
API routes for expense types, auto-category rules, budget rules, and split rules.
"""
from decimal import Decimal
from flask import request, jsonify

from extensions import db
from models import (
    ExpenseType, AutoCategoryRule, BudgetRule, BudgetRuleExpenseType,
    SplitRule, SplitRuleExpenseType, HouseholdMember
)
from decorators import household_required
from household_context import get_current_household_id, get_current_household_members
from blueprints.api import api_bp


# ============================================================================
# Expense Types API Routes
# ============================================================================

@api_bp.route('/api/expense-types', methods=['GET'])
@household_required
def get_expense_types():
    """Get all expense types for the current household."""
    household_id = get_current_household_id()

    expense_types = ExpenseType.query.filter_by(
        household_id=household_id,
        is_active=True
    ).order_by(ExpenseType.name).all()

    return jsonify({
        'success': True,
        'expense_types': [et.to_dict() for et in expense_types]
    })


@api_bp.route('/api/expense-types', methods=['POST'])
@household_required
def create_expense_type():
    """Create a new expense type."""
    try:
        household_id = get_current_household_id()
        data = request.json

        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required.'}), 400

        # Check for duplicate name
        existing = ExpenseType.query.filter_by(
            household_id=household_id,
            name=name
        ).first()

        if existing:
            if existing.is_active:
                return jsonify({'success': False, 'error': 'An expense type with this name already exists.'}), 400
            else:
                # Reactivate existing expense type
                existing.is_active = True
                existing.icon = data.get('icon')
                existing.color = data.get('color')
                db.session.commit()
                return jsonify({'success': True, 'expense_type': existing.to_dict()})

        expense_type = ExpenseType(
            household_id=household_id,
            name=name,
            icon=data.get('icon'),
            color=data.get('color')
        )

        db.session.add(expense_type)
        db.session.commit()

        return jsonify({'success': True, 'expense_type': expense_type.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/expense-types/<int:expense_type_id>', methods=['PUT'])
@household_required
def update_expense_type(expense_type_id):
    """Update an expense type."""
    try:
        household_id = get_current_household_id()

        expense_type = ExpenseType.query.filter_by(
            id=expense_type_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'success': False, 'error': 'Name cannot be empty.'}), 400

            # Check for duplicate name
            existing = ExpenseType.query.filter(
                ExpenseType.household_id == household_id,
                ExpenseType.name == name,
                ExpenseType.id != expense_type_id
            ).first()

            if existing:
                return jsonify({'success': False, 'error': 'An expense type with this name already exists.'}), 400

            expense_type.name = name

        if 'icon' in data:
            expense_type.icon = data['icon']

        if 'color' in data:
            expense_type.color = data['color']

        db.session.commit()

        return jsonify({'success': True, 'expense_type': expense_type.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/expense-types/<int:expense_type_id>', methods=['DELETE'])
@household_required
def delete_expense_type(expense_type_id):
    """Deactivate an expense type (soft delete)."""
    try:
        household_id = get_current_household_id()

        expense_type = ExpenseType.query.filter_by(
            id=expense_type_id,
            household_id=household_id
        ).first_or_404()

        # Check if expense type is used in budget rules
        budget_usage = BudgetRuleExpenseType.query.filter_by(
            expense_type_id=expense_type_id
        ).join(BudgetRule).filter(
            BudgetRule.is_active.is_(True)
        ).first()

        if budget_usage:
            return jsonify({
                'success': False,
                'error': 'Cannot delete expense type that is used in active budget rules.'
            }), 400

        # Soft delete
        expense_type.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# Auto-Category Rules API Routes
# ============================================================================

@api_bp.route('/api/auto-category-rules', methods=['GET'])
@household_required
def get_auto_category_rules():
    """Get all auto-category rules for the current household."""
    household_id = get_current_household_id()

    rules = AutoCategoryRule.query.filter_by(
        household_id=household_id
    ).order_by(AutoCategoryRule.priority.desc(), AutoCategoryRule.keyword).all()

    return jsonify({
        'success': True,
        'rules': [r.to_dict() for r in rules]
    })


@api_bp.route('/api/auto-category-rules', methods=['POST'])
@household_required
def create_auto_category_rule():
    """Create a new auto-category rule."""
    try:
        household_id = get_current_household_id()
        data = request.json

        keyword = data.get('keyword', '').strip()
        expense_type_id = data.get('expense_type_id')

        if not keyword:
            return jsonify({'success': False, 'error': 'Keyword is required.'}), 400

        if not expense_type_id:
            return jsonify({'success': False, 'error': 'Expense type is required.'}), 400

        # Verify expense type belongs to household
        expense_type = ExpenseType.query.filter_by(
            id=expense_type_id,
            household_id=household_id,
            is_active=True
        ).first()

        if not expense_type:
            return jsonify({'success': False, 'error': 'Invalid expense type.'}), 400

        rule = AutoCategoryRule(
            household_id=household_id,
            keyword=keyword,
            expense_type_id=expense_type_id,
            priority=data.get('priority', 0)
        )

        db.session.add(rule)
        db.session.commit()

        return jsonify({'success': True, 'rule': rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/auto-category-rules/<int:rule_id>', methods=['PUT'])
@household_required
def update_auto_category_rule(rule_id):
    """Update an auto-category rule."""
    try:
        household_id = get_current_household_id()

        rule = AutoCategoryRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        if 'keyword' in data:
            keyword = data['keyword'].strip()
            if not keyword:
                return jsonify({'success': False, 'error': 'Keyword cannot be empty.'}), 400
            rule.keyword = keyword

        if 'expense_type_id' in data:
            expense_type = ExpenseType.query.filter_by(
                id=data['expense_type_id'],
                household_id=household_id,
                is_active=True
            ).first()

            if not expense_type:
                return jsonify({'success': False, 'error': 'Invalid expense type.'}), 400

            rule.expense_type_id = data['expense_type_id']

        if 'priority' in data:
            rule.priority = data['priority']

        db.session.commit()

        return jsonify({'success': True, 'rule': rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/auto-category-rules/<int:rule_id>', methods=['DELETE'])
@household_required
def delete_auto_category_rule(rule_id):
    """Delete an auto-category rule."""
    try:
        household_id = get_current_household_id()

        rule = AutoCategoryRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        db.session.delete(rule)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/auto-categorize', methods=['POST'])
@household_required
def auto_categorize():
    """Get suggested expense type for a merchant name."""
    household_id = get_current_household_id()
    data = request.json

    merchant = data.get('merchant', '').strip().lower()

    if not merchant:
        return jsonify({'success': True, 'expense_type': None})

    # Find matching rule (highest priority first)
    rules = AutoCategoryRule.query.filter_by(
        household_id=household_id
    ).order_by(AutoCategoryRule.priority.desc()).all()

    for rule in rules:
        if rule.keyword.lower() in merchant:
            return jsonify({
                'success': True,
                'expense_type': rule.expense_type.to_dict() if rule.expense_type else None,
                'matched_rule': rule.to_dict()
            })

    return jsonify({'success': True, 'expense_type': None})


# ============================================================================
# Budget Rules API Routes
# ============================================================================

@api_bp.route('/api/budget-rules', methods=['GET'])
@household_required
def get_budget_rules():
    """Get all budget rules for the current household."""
    household_id = get_current_household_id()

    rules = BudgetRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    return jsonify({
        'success': True,
        'rules': [r.to_dict() for r in rules]
    })


@api_bp.route('/api/budget-rules', methods=['POST'])
@household_required
def create_budget_rule():
    """Create a new budget rule."""
    try:
        household_id = get_current_household_id()
        data = request.json

        giver_user_id = data.get('giver_user_id')
        receiver_user_id = data.get('receiver_user_id')
        monthly_amount = data.get('monthly_amount')
        expense_type_ids = data.get('expense_type_ids', [])

        # Validation
        if not giver_user_id or not receiver_user_id:
            return jsonify({'success': False, 'error': 'Giver and receiver are required.'}), 400

        if giver_user_id == receiver_user_id:
            return jsonify({'success': False, 'error': 'Giver and receiver must be different.'}), 400

        if not monthly_amount or float(monthly_amount) <= 0:
            return jsonify({'success': False, 'error': 'Monthly amount must be positive.'}), 400

        if not expense_type_ids:
            return jsonify({'success': False, 'error': 'At least one expense type is required.'}), 400

        # Verify both users are members of household
        for user_id in [giver_user_id, receiver_user_id]:
            member = HouseholdMember.query.filter_by(
                household_id=household_id,
                user_id=user_id
            ).first()
            if not member:
                return jsonify({'success': False, 'error': 'Invalid user selected.'}), 400

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
                    'success': False,
                    'error': f'Expense type "{expense_type.name}" is already used in another budget rule.'
                }), 400

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

        return jsonify({'success': True, 'rule': budget_rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/budget-rules/<int:rule_id>', methods=['PUT'])
@household_required
def update_budget_rule(rule_id):
    """Update a budget rule."""
    try:
        household_id = get_current_household_id()

        budget_rule = BudgetRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        if 'monthly_amount' in data:
            amount = float(data['monthly_amount'])
            if amount <= 0:
                return jsonify({'success': False, 'error': 'Monthly amount must be positive.'}), 400
            budget_rule.monthly_amount = Decimal(str(amount))

        if 'expense_type_ids' in data:
            expense_type_ids = data['expense_type_ids']

            if not expense_type_ids:
                return jsonify({'success': False, 'error': 'At least one expense type is required.'}), 400

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
                        'success': False,
                        'error': f'Expense type "{expense_type.name}" is already used in another budget rule.'
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

        return jsonify({'success': True, 'rule': budget_rule.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/budget-rules/<int:rule_id>', methods=['DELETE'])
@household_required
def delete_budget_rule(rule_id):
    """Deactivate a budget rule (soft delete)."""
    try:
        household_id = get_current_household_id()

        budget_rule = BudgetRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        budget_rule.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# Split Rules API Routes
# ============================================================================

@api_bp.route('/api/split-rules', methods=['GET'])
@household_required
def get_split_rules():
    """Get all split rules for the current household."""
    household_id = get_current_household_id()
    household_members = get_current_household_members()

    rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    return jsonify({
        'success': True,
        'rules': [r.to_dict(household_members) for r in rules]
    })


@api_bp.route('/api/split-rules', methods=['POST'])
@household_required
def create_split_rule():
    """Create a new split rule."""
    try:
        household_id = get_current_household_id()
        household_members = get_current_household_members()
        data = request.json

        member1_percent = int(data.get('member1_percent', 50))
        member2_percent = int(data.get('member2_percent', 50))
        is_default = bool(data.get('is_default', False))
        expense_type_ids = data.get('expense_type_ids', [])

        # Validation
        if member1_percent + member2_percent != 100:
            return jsonify({'success': False, 'error': 'Percentages must sum to 100.'}), 400

        if member1_percent < 0 or member2_percent < 0:
            return jsonify({'success': False, 'error': 'Percentages cannot be negative.'}), 400

        # If it's a default rule, check no other default exists
        if is_default:
            existing_default = SplitRule.query.filter_by(
                household_id=household_id,
                is_default=True,
                is_active=True
            ).first()
            if existing_default:
                return jsonify({'success': False, 'error': 'A default split rule already exists.'}), 400
        else:
            # Non-default rules require expense types
            if not expense_type_ids:
                return jsonify({'success': False, 'error': 'Select at least one expense category, or mark as default.'}), 400

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
        # Auto-remove from other rules if already assigned (per design spec)
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

        # Auto-delete any rules that are now empty (no expense types and not default)
        _cleanup_empty_split_rules(household_id, exclude_rule_id=rule.id)

        return jsonify({'success': True, 'rule': rule.to_dict(household_members)})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/split-rules/<int:rule_id>', methods=['PUT'])
@household_required
def update_split_rule(rule_id):
    """Update a split rule."""
    try:
        household_id = get_current_household_id()
        household_members = get_current_household_members()

        split_rule = SplitRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        data = request.json

        # Update percentages
        if 'member1_percent' in data and 'member2_percent' in data:
            member1_percent = int(data['member1_percent'])
            member2_percent = int(data['member2_percent'])

            if member1_percent + member2_percent != 100:
                return jsonify({'success': False, 'error': 'Percentages must sum to 100.'}), 400

            if member1_percent < 0 or member2_percent < 0:
                return jsonify({'success': False, 'error': 'Percentages cannot be negative.'}), 400

            split_rule.member1_percent = member1_percent
            split_rule.member2_percent = member2_percent

        # Update expense types
        if 'expense_type_ids' in data:
            expense_type_ids = data['expense_type_ids']

            # Non-default rules need at least one expense type
            if not split_rule.is_default and not expense_type_ids:
                return jsonify({'success': False, 'error': 'Non-default rules require at least one expense category.'}), 400

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

        return jsonify({'success': True, 'rule': split_rule.to_dict(household_members)})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/api/split-rules/<int:rule_id>', methods=['DELETE'])
@household_required
def delete_split_rule(rule_id):
    """Deactivate a split rule (soft delete)."""
    try:
        household_id = get_current_household_id()

        split_rule = SplitRule.query.filter_by(
            id=rule_id,
            household_id=household_id
        ).first_or_404()

        split_rule.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


def _cleanup_empty_split_rules(household_id, exclude_rule_id=None):
    """Delete split rules that have no expense types and are not default."""
    rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True,
        is_default=False
    ).all()

    for rule in rules:
        if rule.id == exclude_rule_id:
            continue
        # Check if rule has any expense types
        if not rule.expense_types:
            rule.is_active = False

    db.session.commit()
