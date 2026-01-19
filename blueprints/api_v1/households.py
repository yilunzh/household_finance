"""
Household API routes for mobile app.

Endpoints:
- GET /api/v1/households - List user's households
- POST /api/v1/households - Create new household
- GET /api/v1/households/<id> - Get household details
- GET /api/v1/households/<id>/members - Get household members
"""
from flask import request, jsonify, g

from extensions import db
from models import Household, HouseholdMember, User, ExpenseType
from api_decorators import jwt_required, api_household_required, api_household_owner_required
from blueprints.api_v1 import api_v1_bp


def _household_to_dict(household, user_id=None):
    """Convert household to API response dict."""
    data = {
        'id': household.id,
        'name': household.name,
        'created_at': household.created_at.isoformat(),
        'created_by_user_id': household.created_by_user_id
    }

    # If user_id provided, include their role
    if user_id:
        member = HouseholdMember.query.filter_by(
            household_id=household.id,
            user_id=user_id
        ).first()
        if member:
            data['role'] = member.role
            data['display_name'] = member.display_name

    return data


def _member_to_dict(member):
    """Convert household member to API response dict."""
    user = User.query.get(member.user_id)
    return {
        'id': member.id,
        'user_id': member.user_id,
        'display_name': member.display_name,
        'role': member.role,
        'joined_at': member.joined_at.isoformat(),
        'email': user.email if user else None,
        'name': user.name if user else None
    }


def _create_default_expense_types(household_id):
    """Create default expense types for a new household."""
    default_types = [
        {'name': 'Grocery', 'icon': 'cart', 'color': 'emerald'},
        {'name': 'Dining', 'icon': 'utensils', 'color': 'amber'},
        {'name': 'Household', 'icon': 'home', 'color': 'blue'},
        {'name': 'Entertainment', 'icon': 'ticket', 'color': 'purple'},
        {'name': 'Transportation', 'icon': 'car', 'color': 'gray'},
        {'name': 'Healthcare', 'icon': 'heart', 'color': 'red'},
        {'name': 'Shopping', 'icon': 'bag', 'color': 'pink'},
        {'name': 'Other', 'icon': 'ellipsis', 'color': 'slate'},
    ]

    for et_data in default_types:
        expense_type = ExpenseType(
            household_id=household_id,
            name=et_data['name'],
            icon=et_data['icon'],
            color=et_data['color']
        )
        db.session.add(expense_type)


@api_v1_bp.route('/households', methods=['GET'])
@jwt_required
def api_list_households():
    """List all households the current user belongs to.

    Returns:
        {
            "households": [...]
        }
    """
    user_id = g.current_user_id

    memberships = HouseholdMember.query.filter_by(user_id=user_id).all()

    households = []
    for membership in memberships:
        household = Household.query.get(membership.household_id)
        if household:
            data = _household_to_dict(household, user_id)
            households.append(data)

    return jsonify({
        'households': households
    })


@api_v1_bp.route('/households', methods=['POST'])
@jwt_required
def api_create_household():
    """Create a new household.

    Request body:
        {
            "name": "Home",
            "display_name": "Alice"  # User's display name in this household
        }

    Returns:
        {"household": {...}}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    name = data.get('name', '').strip()
    display_name = data.get('display_name', '').strip()

    if not name:
        return jsonify({'error': 'Household name is required'}), 400

    if not display_name:
        # Default to user's name
        display_name = g.current_user.name

    try:
        # Create household
        household = Household(
            name=name,
            created_by_user_id=g.current_user_id
        )
        db.session.add(household)
        db.session.flush()  # Get the ID

        # Add creator as owner
        member = HouseholdMember(
            household_id=household.id,
            user_id=g.current_user_id,
            role='owner',
            display_name=display_name
        )
        db.session.add(member)

        # Create default expense types
        _create_default_expense_types(household.id)

        db.session.commit()

        return jsonify({
            'household': _household_to_dict(household, g.current_user_id)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create household'}), 500


@api_v1_bp.route('/households/<int:household_id>', methods=['GET'])
@jwt_required
def api_get_household(household_id):
    """Get household details.

    User must be a member of the household.

    Returns:
        {"household": {...}, "members": [...]}
    """
    # Verify membership
    member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=g.current_user_id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this household'}), 403

    household = Household.query.get(household_id)
    if not household:
        return jsonify({'error': 'Household not found'}), 404

    # Get all members
    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    return jsonify({
        'household': _household_to_dict(household, g.current_user_id),
        'members': [_member_to_dict(m) for m in members]
    })


@api_v1_bp.route('/households/<int:household_id>/members', methods=['GET'])
@jwt_required
def api_get_household_members(household_id):
    """Get all members of a household.

    User must be a member of the household.

    Returns:
        {"members": [...]}
    """
    # Verify membership
    member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=g.current_user_id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this household'}), 403

    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    return jsonify({
        'members': [_member_to_dict(m) for m in members]
    })


@api_v1_bp.route('/households/<int:household_id>/leave', methods=['POST'])
@jwt_required
def api_leave_household(household_id):
    """Leave a household.

    Owners cannot leave unless they are the only member.

    Returns:
        {"success": true}
    """
    member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=g.current_user_id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this household'}), 403

    # Check if owner trying to leave
    if member.role == 'owner':
        # Count other members
        member_count = HouseholdMember.query.filter_by(household_id=household_id).count()
        if member_count > 1:
            return jsonify({'error': 'Owners cannot leave while other members exist. Transfer ownership first.'}), 400

    try:
        db.session.delete(member)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to leave household'}), 500
