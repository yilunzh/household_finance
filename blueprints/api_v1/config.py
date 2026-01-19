"""
Configuration API routes for mobile app.

Endpoints:
- GET /api/v1/expense-types - List expense types
- GET /api/v1/split-rules - List split rules
- GET /api/v1/categories - List transaction categories
"""
from flask import jsonify, g

from models import ExpenseType, SplitRule, HouseholdMember
from api_decorators import jwt_required, api_household_required
from blueprints.api_v1 import api_v1_bp


# Transaction category definitions
TRANSACTION_CATEGORIES = [
    {'code': 'SHARED', 'name': 'Shared', 'description': 'Split between household members'},
    {'code': 'I_PAY_FOR_WIFE', 'name': 'For Partner (by me)', 'description': 'Paid by member 1 for member 2'},
    {'code': 'WIFE_PAYS_FOR_ME', 'name': 'For Me (by partner)', 'description': 'Paid by member 2 for member 1'},
    {'code': 'PERSONAL_ME', 'name': 'Personal', 'description': 'Personal expense (member 1)'},
    {'code': 'PERSONAL_WIFE', 'name': 'Personal (partner)', 'description': 'Personal expense (member 2)'},
]


@api_v1_bp.route('/expense-types', methods=['GET'])
@jwt_required
@api_household_required
def api_get_expense_types():
    """Get all expense types for the current household.

    Returns:
        {
            "expense_types": [
                {"id": 1, "name": "Grocery", "icon": "cart", "color": "emerald"},
                ...
            ]
        }
    """
    household_id = g.household_id

    expense_types = ExpenseType.query.filter_by(
        household_id=household_id,
        is_active=True
    ).order_by(ExpenseType.name).all()

    return jsonify({
        'expense_types': [et.to_dict() for et in expense_types]
    })


@api_v1_bp.route('/split-rules', methods=['GET'])
@jwt_required
@api_household_required
def api_get_split_rules():
    """Get all split rules for the current household.

    Returns:
        {
            "split_rules": [
                {
                    "id": 1,
                    "member1_percent": 60,
                    "member2_percent": 40,
                    "is_default": false,
                    "expense_type_ids": [1, 2],
                    "description": "Alice 60%, Bob 40%"
                },
                ...
            ],
            "members": [
                {"user_id": 1, "display_name": "Alice", "role": "owner"},
                {"user_id": 2, "display_name": "Bob", "role": "member"}
            ]
        }
    """
    household_id = g.household_id

    # Get members for split description
    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    split_rules = SplitRule.query.filter_by(
        household_id=household_id,
        is_active=True
    ).all()

    return jsonify({
        'split_rules': [rule.to_dict(members) for rule in split_rules],
        'members': [
            {
                'user_id': m.user_id,
                'display_name': m.display_name,
                'role': m.role
            }
            for m in members
        ]
    })


@api_v1_bp.route('/categories', methods=['GET'])
@jwt_required
@api_household_required
def api_get_categories():
    """Get transaction categories with dynamic names based on household members.

    Returns:
        {
            "categories": [
                {"code": "SHARED", "name": "Shared", "description": "..."},
                {"code": "I_PAY_FOR_WIFE", "name": "For Bob (by Alice)", "description": "..."},
                ...
            ]
        }
    """
    household_id = g.household_id

    # Get members to personalize category names
    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    # Find owner (member1) and other member (member2)
    owner = next((m for m in members if m.role == 'owner'), None)
    other = next((m for m in members if m.role != 'owner'), None)

    if owner and other:
        name1 = owner.display_name
        name2 = other.display_name

        categories = [
            {'code': 'SHARED', 'name': 'Shared', 'description': f'Split between {name1} and {name2}'},
            {'code': 'I_PAY_FOR_WIFE', 'name': f'For {name2} (by {name1})', 'description': f'{name1} pays for {name2}'},
            {'code': 'WIFE_PAYS_FOR_ME', 'name': f'For {name1} (by {name2})', 'description': f'{name2} pays for {name1}'},
            {'code': 'PERSONAL_ME', 'name': f'Personal ({name1})', 'description': f'{name1}\'s personal expense'},
            {'code': 'PERSONAL_WIFE', 'name': f'Personal ({name2})', 'description': f'{name2}\'s personal expense'},
        ]
    else:
        # Fallback to generic names
        categories = TRANSACTION_CATEGORIES

    return jsonify({
        'categories': categories
    })
