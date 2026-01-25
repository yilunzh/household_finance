"""
Invitation API routes for mobile app.

Endpoints:
- POST /api/v1/households/<id>/invitations - Send invitation
- GET /api/v1/households/<id>/invitations - List pending invitations
- DELETE /api/v1/invitations/<id> - Cancel invitation
- GET /api/v1/invitations/<token> - Get invitation details (public)
- POST /api/v1/invitations/<token>/accept - Accept invitation
"""
import os
import secrets
from datetime import datetime, timedelta
from flask import request, jsonify, g

from extensions import db
from models import Household, HouseholdMember, User, Invitation
from api_decorators import jwt_required
from email_service import send_invitation_email
from blueprints.api_v1 import api_v1_bp
from blueprints.api_v1.auth import is_valid_email


def _invitation_to_dict(invitation, include_token=False):
    """Convert invitation to API response dict."""
    inviter = User.query.get(invitation.invited_by_user_id)
    household = Household.query.get(invitation.household_id)

    data = {
        'id': invitation.id,
        'email': invitation.email,
        'status': invitation.status,
        'expires_at': invitation.expires_at.isoformat(),
        'created_at': invitation.created_at.isoformat(),
        'invited_by': {
            'id': inviter.id,
            'name': inviter.name,
            'email': inviter.email
        } if inviter else None,
        'household': {
            'id': household.id,
            'name': household.name
        } if household else None
    }

    if include_token:
        data['token'] = invitation.token

    if invitation.accepted_at:
        data['accepted_at'] = invitation.accepted_at.isoformat()

    return data


@api_v1_bp.route('/households/<int:household_id>/invitations', methods=['POST'])
@jwt_required
def api_send_invitation(household_id):
    """Send an invitation to join the household.

    Request body:
        {
            "email": "newuser@example.com"
        }

    Returns:
        {
            "invitation": {...},
            "invite_url": "https://...",
            "email_sent": true/false
        }
    """
    # Verify membership
    member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=g.current_user_id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this household'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email address'}), 400

    household = Household.query.get(household_id)
    if not household:
        return jsonify({'error': 'Household not found'}), 404

    # Check if email is already a member of this household
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        existing_member = HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=existing_user.id
        ).first()
        if existing_member:
            return jsonify({'error': 'This user is already a member of your household'}), 400

    # Check for existing pending invitation
    existing_invite = Invitation.query.filter_by(
        household_id=household_id,
        email=email,
        status='pending'
    ).first()
    if existing_invite:
        if existing_invite.is_valid():
            return jsonify({'error': 'An invitation has already been sent to this email'}), 400
        else:
            # Mark old invitation as expired
            existing_invite.status = 'expired'
            db.session.commit()

    try:
        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Create invitation
        invitation = Invitation(
            household_id=household_id,
            email=email,
            token=token,
            status='pending',
            expires_at=datetime.utcnow() + timedelta(days=7),
            invited_by_user_id=g.current_user_id
        )
        db.session.add(invitation)
        db.session.commit()

        # Send email
        email_sent = send_invitation_email(invitation, household, g.current_user)

        # Build invite URLs
        site_url = os.environ.get('SITE_URL', 'http://localhost:5001')
        web_url = f"{site_url}/invite/accept?token={token}"
        deep_link_url = f"householdtracker://invite/{token}"

        return jsonify({
            'invitation': _invitation_to_dict(invitation, include_token=True),
            'invite_url': web_url,
            'deep_link_url': deep_link_url,
            'email_sent': email_sent
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to create invitation'}), 500


@api_v1_bp.route('/households/<int:household_id>/invitations', methods=['GET'])
@jwt_required
def api_list_invitations(household_id):
    """List pending invitations for the household.

    Returns:
        {
            "invitations": [...]
        }
    """
    # Verify membership
    member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=g.current_user_id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this household'}), 403

    # Get pending invitations
    invitations = Invitation.query.filter_by(
        household_id=household_id,
        status='pending'
    ).order_by(Invitation.created_at.desc()).all()

    # Filter to only valid (non-expired) invitations
    valid_invitations = [inv for inv in invitations if inv.is_valid()]

    return jsonify({
        'invitations': [_invitation_to_dict(inv) for inv in valid_invitations]
    })


@api_v1_bp.route('/invitations/<int:invitation_id>', methods=['DELETE'])
@jwt_required
def api_cancel_invitation(invitation_id):
    """Cancel a pending invitation.

    Returns:
        {"success": true}
    """
    invitation = Invitation.query.get(invitation_id)

    if not invitation:
        return jsonify({'error': 'Invitation not found'}), 404

    # Verify user is a member of the household
    member = HouseholdMember.query.filter_by(
        household_id=invitation.household_id,
        user_id=g.current_user_id
    ).first()

    if not member:
        return jsonify({'error': 'Not authorized to cancel this invitation'}), 403

    if invitation.status != 'pending':
        return jsonify({'error': 'Invitation is not pending'}), 400

    try:
        invitation.status = 'cancelled'
        db.session.commit()

        return jsonify({'success': True})

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel invitation'}), 500


@api_v1_bp.route('/invitations/<token>', methods=['GET'])
def api_get_invitation(token):
    """Get invitation details by token (public endpoint).

    Returns:
        {
            "invitation": {...},
            "household": {...},
            "inviter": {...}
        }
    """
    invitation = Invitation.query.filter_by(token=token).first()

    if not invitation:
        return jsonify({'error': 'Invitation not found'}), 404

    if invitation.status == 'accepted':
        return jsonify({'error': 'Invitation has already been used'}), 400

    if not invitation.is_valid():
        return jsonify({'error': 'Invitation has expired'}), 400

    household = Household.query.get(invitation.household_id)
    inviter = User.query.get(invitation.invited_by_user_id)

    return jsonify({
        'invitation': {
            'id': invitation.id,
            'email': invitation.email,
            'expires_at': invitation.expires_at.isoformat(),
            'created_at': invitation.created_at.isoformat()
        },
        'household': {
            'id': household.id,
            'name': household.name
        } if household else None,
        'inviter': {
            'id': inviter.id,
            'name': inviter.name
        } if inviter else None
    })


@api_v1_bp.route('/invitations/<token>/accept', methods=['POST'])
@jwt_required
def api_accept_invitation(token):
    """Accept an invitation to join a household.

    Request body (optional):
        {
            "display_name": "My Name"  # Name to display in the household
        }

    Returns:
        {
            "success": true,
            "household": {...}
        }
    """
    invitation = Invitation.query.filter_by(token=token).first()

    if not invitation:
        return jsonify({'error': 'Invitation not found'}), 404

    if invitation.status == 'accepted':
        return jsonify({'error': 'Invitation has already been used'}), 400

    if not invitation.is_valid():
        return jsonify({'error': 'Invitation has expired'}), 400

    # Get display name from request or use user's name
    data = request.get_json(silent=True) or {}
    display_name = data.get('display_name', '').strip()
    if not display_name:
        display_name = g.current_user.name

    household = Household.query.get(invitation.household_id)
    if not household:
        return jsonify({'error': 'Household not found'}), 404

    # Check if already a member
    existing_member = HouseholdMember.query.filter_by(
        household_id=invitation.household_id,
        user_id=g.current_user_id
    ).first()

    if existing_member:
        return jsonify({'error': 'You are already a member of this household'}), 400

    try:
        # Add user to household
        member = HouseholdMember(
            household_id=invitation.household_id,
            user_id=g.current_user_id,
            role='member',
            display_name=display_name
        )
        db.session.add(member)

        # Mark invitation as accepted
        invitation.status = 'accepted'
        invitation.accepted_at = datetime.utcnow()

        db.session.commit()

        # Get updated household with user's role
        return jsonify({
            'success': True,
            'household': {
                'id': household.id,
                'name': household.name,
                'role': 'member',
                'display_name': display_name,
                'created_at': household.created_at.isoformat()
            }
        })

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to accept invitation'}), 500
