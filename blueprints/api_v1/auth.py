"""
Authentication API routes for mobile app.

Endpoints:
- POST /api/v1/auth/register - Register new user
- POST /api/v1/auth/login - Login and get tokens
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - Logout (revoke refresh token)
- POST /api/v1/auth/forgot-password - Request password reset
- GET /api/v1/user/me - Get current user profile
- PUT /api/v1/user/profile - Update display name
- PUT /api/v1/user/password - Change password
- POST /api/v1/user/email/request - Request email change
- POST /api/v1/user/email/cancel - Cancel pending email change
- DELETE /api/v1/user - Delete account
"""
import logging
import re
import secrets
from datetime import datetime, timedelta

from flask import request, jsonify, g

from extensions import db, limiter


# Email validation regex pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def is_valid_email(email):
    """Validate email format using regex."""
    return EMAIL_REGEX.match(email) is not None


def validate_password_strength(password):
    """Validate password meets strength requirements.

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if len(password) < 8:
        return False, 'Password must be at least 8 characters'
    if len(password) > 128:
        return False, 'Password is too long (max 128 characters)'
    if not any(c.isupper() for c in password):
        return False, 'Password must contain at least one uppercase letter'
    if not any(c.islower() for c in password):
        return False, 'Password must contain at least one lowercase letter'
    if not any(c.isdigit() for c in password):
        return False, 'Password must contain at least one number'
    return True, None


from models import User, HouseholdMember, Household, Transaction
from api_decorators import (
    generate_access_token,
    generate_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    jwt_required
)
from blueprints.api_v1 import api_v1_bp

logger = logging.getLogger(__name__)


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

    # Validate email format
    if not is_valid_email(email):
        return jsonify({'error': 'Please enter a valid email address'}), 400

    # Validate password strength
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

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

    except Exception:
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


@api_v1_bp.route('/user/profile', methods=['PUT'])
@jwt_required
def api_update_profile():
    """Update user's display name.

    Request body:
        {
            "name": "New Display Name"
        }

    Returns:
        {
            "user": {...}
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    if len(name) > 100:
        return jsonify({'error': 'Name is too long (max 100 characters)'}), 400

    user = g.current_user
    user.name = name
    db.session.commit()

    logger.info(f"Profile updated for user: {user.email}")

    return jsonify({
        'user': _user_to_dict(user)
    })


@api_v1_bp.route('/user/password', methods=['PUT'])
@jwt_required
def api_change_password():
    """Change user's password.

    Request body:
        {
            "current_password": "oldpassword",
            "new_password": "newpassword"
        }

    Returns:
        {"success": true}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password required'}), 400

    user = g.current_user

    # Verify current password
    if not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

    # Update password
    user.set_password(new_password)
    db.session.commit()

    logger.info(f"Password changed for user: {user.email}")

    return jsonify({'success': True})


@api_v1_bp.route('/user/email/request', methods=['POST'])
@jwt_required
def api_request_email_change():
    """Request email change - sends verification to new email.

    Request body:
        {
            "new_email": "newemail@example.com",
            "password": "currentpassword"
        }

    Returns:
        {"success": true, "message": "Verification email sent"}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    new_email = data.get('new_email', '').strip().lower()
    password = data.get('password', '')

    if not new_email or not password:
        return jsonify({'error': 'New email and password required'}), 400

    user = g.current_user

    # Verify password
    if not user.check_password(password):
        return jsonify({'error': 'Password is incorrect'}), 401

    # Validate email format
    if not is_valid_email(new_email):
        return jsonify({'error': 'Please enter a valid email address'}), 400

    # Check if email is same as current
    if new_email == user.email:
        return jsonify({'error': 'This is already your email address'}), 400

    # Check if email is already in use
    existing = User.query.filter_by(email=new_email).first()
    if existing:
        return jsonify({'error': 'This email address is already in use'}), 409

    # Generate verification token
    token = secrets.token_urlsafe(32)
    user.pending_email = new_email
    user.email_change_token = token
    user.email_change_expires = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    # Send verification email
    try:
        from email_service import send_email_change_verification
        send_email_change_verification(user, new_email, token)
    except Exception as e:
        logger.error(f"Failed to send email change verification: {e}")
        return jsonify({'error': 'Failed to send verification email'}), 500

    logger.info(f"Email change requested for user: {user.email} -> {new_email}")

    return jsonify({
        'success': True,
        'message': 'Verification email sent to new address'
    })


@api_v1_bp.route('/user/email/cancel', methods=['POST'])
@jwt_required
def api_cancel_email_change():
    """Cancel pending email change.

    Returns:
        {"success": true}
    """
    user = g.current_user

    if not user.pending_email:
        return jsonify({'error': 'No pending email change'}), 400

    user.pending_email = None
    user.email_change_token = None
    user.email_change_expires = None
    db.session.commit()

    logger.info(f"Email change cancelled for user: {user.email}")

    return jsonify({'success': True})


@api_v1_bp.route('/user', methods=['DELETE'])
@jwt_required
def api_delete_account():
    """Delete user account and anonymize transactions.

    Request body:
        {
            "password": "currentpassword",
            "confirm": "DELETE"
        }

    Returns:
        {"success": true}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    password = data.get('password', '')
    confirm = data.get('confirm', '')

    if not password:
        return jsonify({'error': 'Password is required'}), 400

    if confirm != 'DELETE':
        return jsonify({'error': 'Please confirm deletion by sending confirm: "DELETE"'}), 400

    user = g.current_user

    # Verify password
    if not user.check_password(password):
        return jsonify({'error': 'Password is incorrect'}), 401

    user_id = user.id
    user_email = user.email

    # Revoke all tokens for this user
    revoke_all_user_tokens(user_id)

    # Anonymize transactions - set paid_by_user_id to NULL
    Transaction.query.filter_by(paid_by_user_id=user_id).update({'paid_by_user_id': None})

    # Handle household memberships
    for membership in user.household_memberships:
        household = membership.household
        member_count = HouseholdMember.query.filter_by(household_id=household.id).count()

        if member_count == 1:
            # Sole member - delete household (transactions already anonymized)
            db.session.delete(household)
        elif membership.role == 'owner':
            # Transfer ownership to another member
            other_member = HouseholdMember.query.filter(
                HouseholdMember.household_id == household.id,
                HouseholdMember.user_id != user_id
            ).first()
            if other_member:
                other_member.role = 'owner'

    # Delete user (CASCADE handles HouseholdMember records)
    db.session.delete(user)
    db.session.commit()

    logger.info(f"Account deleted via API for user: {user_email}")

    return jsonify({'success': True})


@api_v1_bp.route('/auth/forgot-password', methods=['POST'])
@limiter.limit('5 per hour')
def api_forgot_password():
    """Request password reset - sends email with link to web reset page.

    Request body:
        {
            "email": "user@example.com"
        }

    Returns:
        {"success": true, "message": "If account exists, reset email sent"}

    Note: Always returns success to prevent email enumeration.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    # Find user - but don't reveal if they exist
    user = User.query.filter_by(email=email).first()

    if user:
        # Generate reset token
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        # Send email with link to web reset page
        try:
            from email_service import send_password_reset_email
            send_password_reset_email(user, token)
            logger.info(f"Password reset requested via API for: {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            # Don't reveal error to prevent email enumeration

    # Always return success to prevent email enumeration
    return jsonify({
        'success': True,
        'message': 'If an account with this email exists, a reset link has been sent'
    })
