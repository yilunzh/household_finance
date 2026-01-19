"""
JWT authentication decorators for mobile API.
"""
import os
import uuid
from functools import wraps
from datetime import datetime, timedelta

import jwt
from flask import request, jsonify, g, current_app

from models import User, HouseholdMember, RefreshToken
from extensions import db


# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', os.environ.get('SECRET_KEY', 'dev-secret-key'))
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
JWT_ALGORITHM = 'HS256'


def generate_access_token(user_id, household_id=None):
    """Generate a short-lived access token.

    Args:
        user_id: The user's ID
        household_id: Optional current household context

    Returns:
        JWT access token string
    """
    payload = {
        'sub': user_id,
        'type': 'access',
        'household_id': household_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user_id, device_name=None):
    """Generate a long-lived refresh token and store it in the database.

    Args:
        user_id: The user's ID
        device_name: Optional device identifier (e.g., "iPhone 15 Pro")

    Returns:
        Tuple of (token_string, RefreshToken model instance)
    """
    token_jti = str(uuid.uuid4())
    expires_at = datetime.utcnow() + JWT_REFRESH_TOKEN_EXPIRES

    payload = {
        'sub': user_id,
        'type': 'refresh',
        'jti': token_jti,
        'iat': datetime.utcnow(),
        'exp': expires_at
    }

    token_string = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    # Store in database for revocation tracking
    refresh_token = RefreshToken(
        user_id=user_id,
        token_jti=token_jti,
        device_name=device_name,
        expires_at=expires_at
    )
    db.session.add(refresh_token)
    db.session.commit()

    return token_string, refresh_token


def decode_token(token):
    """Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def jwt_required(f):
    """Decorator requiring valid JWT access token.

    Sets g.current_user_id and g.token_household_id from the token.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401

        token = auth_header.replace('Bearer ', '')

        try:
            payload = decode_token(token)

            if payload.get('type') != 'access':
                return jsonify({'error': 'Invalid token type'}), 401

            g.current_user_id = payload['sub']
            g.token_household_id = payload.get('household_id')

            # Verify user exists and is active
            user = User.query.get(g.current_user_id)
            if not user or not user.is_active:
                return jsonify({'error': 'User not found or inactive'}), 401

            g.current_user = user

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated


def api_household_required(f):
    """Decorator requiring valid household context for API requests.

    Must be used after @jwt_required.
    Gets household_id from X-Household-ID header or token.
    Validates user is a member of the household.

    Sets g.household_id and g.household_member.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get household from header (preferred) or token (fallback)
        household_id = request.headers.get('X-Household-ID')

        if household_id:
            try:
                household_id = int(household_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid X-Household-ID header'}), 400
        else:
            # Fallback to household_id embedded in token
            household_id = getattr(g, 'token_household_id', None)

        if not household_id:
            return jsonify({'error': 'Household context required. Set X-Household-ID header.'}), 400

        # Verify user is a member of this household
        member = HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=g.current_user_id
        ).first()

        if not member:
            return jsonify({'error': 'Not a member of this household'}), 403

        g.household_id = household_id
        g.household_member = member

        return f(*args, **kwargs)
    return decorated


def api_household_owner_required(f):
    """Decorator requiring user to be owner of the household.

    Must be used after @jwt_required and @api_household_required.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'household_member'):
            return jsonify({'error': 'Household context not set'}), 400

        if g.household_member.role != 'owner':
            return jsonify({'error': 'Household owner access required'}), 403

        return f(*args, **kwargs)
    return decorated


def validate_refresh_token(token):
    """Validate a refresh token and return the user if valid.

    Args:
        token: JWT refresh token string

    Returns:
        User model if valid, None if invalid

    Also checks the database to ensure token hasn't been revoked.
    """
    try:
        payload = decode_token(token)

        if payload.get('type') != 'refresh':
            return None

        token_jti = payload.get('jti')
        if not token_jti:
            return None

        # Check database for revocation
        stored_token = RefreshToken.query.filter_by(token_jti=token_jti).first()
        if not stored_token or not stored_token.is_valid():
            return None

        # Get user
        user = User.query.get(payload['sub'])
        if not user or not user.is_active:
            return None

        return user

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def revoke_refresh_token(token):
    """Revoke a refresh token.

    Args:
        token: JWT refresh token string

    Returns:
        True if revoked, False if token not found
    """
    try:
        payload = decode_token(token)
        token_jti = payload.get('jti')

        if token_jti:
            stored_token = RefreshToken.query.filter_by(token_jti=token_jti).first()
            if stored_token:
                stored_token.revoke()
                db.session.commit()
                return True

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass

    return False


def revoke_all_user_tokens(user_id):
    """Revoke all refresh tokens for a user (e.g., on password change).

    Args:
        user_id: The user's ID
    """
    RefreshToken.query.filter_by(user_id=user_id, revoked_at=None).update(
        {'revoked_at': datetime.utcnow()}
    )
    db.session.commit()
