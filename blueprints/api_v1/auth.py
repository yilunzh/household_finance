"""
Authentication API routes for mobile app.

Endpoints:
- POST /api/v1/auth/register - Register new user
- POST /api/v1/auth/login - Login and get tokens
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - Logout (revoke refresh token)
"""
from datetime import datetime

from flask import request, jsonify, g

from extensions import db
from models import User, HouseholdMember, Household
from api_decorators import (
    generate_access_token,
    generate_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    jwt_required
)
from blueprints.api_v1 import api_v1_bp


def _get_user_households(user_id):
    """Get all households for a user with their roles.

    Returns:
        List of dicts with household info and user's role
    """
    memberships = HouseholdMember.query.filter_by(user_id=user_id).all()

    households = []
    for membership in memberships:
        household = Household.query.get(membership.household_id)
        if household:
            households.append({
                'id': household.id,
                'name': household.name,
                'role': membership.role,
                'display_name': membership.display_name,
                'joined_at': membership.joined_at.isoformat()
            })

    return households


def _user_to_dict(user):
    """Convert user to API response dict."""
    return {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'created_at': user.created_at.isoformat()
    }


@api_v1_bp.route('/auth/register', methods=['POST'])
def api_register():
    """Register a new user account.

    Request body:
        {
            "email": "user@example.com",
            "password": "securepassword",
            "name": "User Name",
            "device_name": "iPhone 15 Pro"  # optional
        }

    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "user": {...},
            "households": []
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    device_name = data.get('device_name')

    # Validation
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 409

    try:
        # Create user
        user = User(
            email=email,
            name=name,
            is_active=True
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Generate tokens
        access_token = generate_access_token(user.id)
        refresh_token, _ = generate_refresh_token(user.id, device_name)

        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': _user_to_dict(user),
            'households': []  # New user has no households
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500


@api_v1_bp.route('/auth/login', methods=['POST'])
def api_login():
    """Login and get access/refresh tokens.

    Request body:
        {
            "email": "user@example.com",
            "password": "securepassword",
            "device_name": "iPhone 15 Pro"  # optional
        }

    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "user": {...},
            "households": [...]
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    device_name = data.get('device_name')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Find user
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 401

    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Get user's households
    households = _get_user_households(user.id)

    # Default to first household if user has any
    default_household_id = households[0]['id'] if households else None

    # Generate tokens
    access_token = generate_access_token(user.id, household_id=default_household_id)
    refresh_token, _ = generate_refresh_token(user.id, device_name)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': _user_to_dict(user),
        'households': households
    })


@api_v1_bp.route('/auth/refresh', methods=['POST'])
def api_refresh():
    """Refresh access token using refresh token.

    Request body:
        {
            "refresh_token": "...",
            "household_id": 123  # optional, to set new household context
        }

    Returns:
        {
            "access_token": "..."
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    refresh_token = data.get('refresh_token')
    household_id = data.get('household_id')

    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 400

    # Validate refresh token
    user = validate_refresh_token(refresh_token)

    if not user:
        return jsonify({'error': 'Invalid or expired refresh token'}), 401

    # If household_id provided, verify membership
    if household_id:
        member = HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=user.id
        ).first()

        if not member:
            return jsonify({'error': 'Not a member of specified household'}), 403

    # Generate new access token
    access_token = generate_access_token(user.id, household_id=household_id)

    return jsonify({
        'access_token': access_token
    })


@api_v1_bp.route('/auth/logout', methods=['POST'])
@jwt_required
def api_logout():
    """Logout by revoking the refresh token.

    Request body:
        {
            "refresh_token": "..."
        }

    Returns:
        {"success": true}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    refresh_token = data.get('refresh_token')

    if refresh_token:
        revoke_refresh_token(refresh_token)

    return jsonify({'success': True})


@api_v1_bp.route('/user/me', methods=['GET'])
@jwt_required
def api_get_current_user():
    """Get current user profile.

    Returns:
        {
            "user": {...},
            "households": [...]
        }
    """
    user = g.current_user
    households = _get_user_households(user.id)

    return jsonify({
        'user': _user_to_dict(user),
        'households': households
    })
