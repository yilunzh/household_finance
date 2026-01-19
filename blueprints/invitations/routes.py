"""
Invitation routes: send, cancel, accept invitations.
"""
import os
import secrets
from datetime import datetime, timedelta
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_user, current_user

from extensions import db
from models import User, Household, HouseholdMember, Invitation
from decorators import household_required
from household_context import get_current_household_id, get_current_household
from email_service import send_invitation_email, is_mail_configured
from blueprints.invitations import invitations_bp


@invitations_bp.route('/household/invite', methods=['GET', 'POST'])
@household_required
def send_invitation():
    """Send an invitation to join the household."""
    household_id = get_current_household_id()
    household = get_current_household()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        # Validation
        if not email:
            flash('Email address is required.', 'danger')
            return redirect(url_for('invitations.send_invitation'))

        # Check if email is already a member of this household
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            existing_member = HouseholdMember.query.filter_by(
                household_id=household_id,
                user_id=existing_user.id
            ).first()
            if existing_member:
                flash('This user is already a member of your household.', 'warning')
                return redirect(url_for('invitations.send_invitation'))

        # Check for existing pending invitation
        existing_invite = Invitation.query.filter_by(
            household_id=household_id,
            email=email,
            status='pending'
        ).first()
        if existing_invite:
            if existing_invite.is_valid():
                flash('An invitation has already been sent to this email.', 'warning')
                return redirect(url_for('invitations.send_invitation'))
            else:
                # Mark old invitation as expired
                existing_invite.status = 'expired'
                db.session.commit()

        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Create invitation
        invitation = Invitation(
            household_id=household_id,
            email=email,
            token=token,
            status='pending',
            expires_at=datetime.utcnow() + timedelta(days=7),
            invited_by_user_id=current_user.id
        )

        db.session.add(invitation)
        db.session.commit()

        # Send email
        email_sent = send_invitation_email(invitation, household, current_user)

        # Build invite URL for display if email not configured
        site_url = os.environ.get('SITE_URL', 'http://localhost:5001')
        invite_url = f"{site_url}/invite/accept?token={token}"

        return render_template(
            'household/invite_sent.html',
            email=email,
            email_sent=email_sent,
            invite_url=invite_url
        )

    # GET request - show invite form
    pending_invitations = Invitation.query.filter_by(
        household_id=household_id,
        status='pending'
    ).order_by(Invitation.created_at.desc()).all()

    # Filter to only valid (non-expired) invitations
    pending_invitations = [inv for inv in pending_invitations if inv.is_valid()]

    return render_template(
        'household/invite.html',
        household=household,
        pending_invitations=pending_invitations,
        mail_configured=is_mail_configured()
    )


@invitations_bp.route('/household/invite/<int:invitation_id>/cancel', methods=['POST'])
@household_required
def cancel_invitation(invitation_id):
    """Cancel a pending invitation."""
    household_id = get_current_household_id()

    invitation = Invitation.query.filter_by(
        id=invitation_id,
        household_id=household_id,
        status='pending'
    ).first_or_404()

    invitation.status = 'cancelled'
    db.session.commit()

    flash('Invitation has been cancelled.', 'info')
    return redirect(url_for('invitations.send_invitation'))


@invitations_bp.route('/invite/accept', methods=['GET', 'POST'])
def accept_invitation():
    """Accept an invitation to join a household."""
    token = request.args.get('token') or request.form.get('token')

    if not token:
        return render_template('household/invite_invalid.html', reason='not_found')

    # Find invitation by token
    invitation = Invitation.query.filter_by(token=token).first()

    if not invitation:
        return render_template('household/invite_invalid.html', reason='not_found')

    if invitation.status == 'accepted':
        return render_template('household/invite_invalid.html', reason='used')

    if not invitation.is_valid():
        return render_template('household/invite_invalid.html', reason='expired')

    # Get household and inviter info
    household = Household.query.get(invitation.household_id)
    inviter = User.query.get(invitation.invited_by_user_id)

    if request.method == 'POST':
        action = request.form.get('action')
        display_name = request.form.get('display_name', '').strip()

        if action == 'join' and current_user.is_authenticated:
            # Logged-in user joining
            if not display_name:
                display_name = current_user.name

            # Check if already a member
            existing_member = HouseholdMember.query.filter_by(
                household_id=invitation.household_id,
                user_id=current_user.id
            ).first()

            if existing_member:
                flash('You are already a member of this household.', 'warning')
                return redirect(url_for('transactions.index'))

            # Add user to household
            member = HouseholdMember(
                household_id=invitation.household_id,
                user_id=current_user.id,
                role='member',
                display_name=display_name
            )
            db.session.add(member)

            # Mark invitation as accepted
            invitation.status = 'accepted'
            invitation.accepted_at = datetime.utcnow()
            db.session.commit()

            flash(f'Welcome to {household.name}!', 'success')
            return redirect(url_for('transactions.index'))

        elif action == 'signup':
            # New user signup
            email = invitation.email  # Use invitation email
            name = request.form.get('name', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not display_name:
                display_name = name

            # Validation
            if not name or not password:
                flash('Name and password are required.', 'danger')
                return render_template(
                    'household/accept_invite.html',
                    invitation=invitation,
                    household=household,
                    inviter=inviter,
                    token=token
                )

            if len(password) < 8:
                flash('Password must be at least 8 characters.', 'danger')
                return render_template(
                    'household/accept_invite.html',
                    invitation=invitation,
                    household=household,
                    inviter=inviter,
                    token=token
                )

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template(
                    'household/accept_invite.html',
                    invitation=invitation,
                    household=household,
                    inviter=inviter,
                    token=token
                )

            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('An account with this email already exists. Please log in instead.', 'warning')
                return redirect(url_for('auth.login', next=url_for('invitations.accept_invitation', token=token)))

            # Create new user
            user = User(email=email, name=name)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # Get user ID

            # Add user to household
            member = HouseholdMember(
                household_id=invitation.household_id,
                user_id=user.id,
                role='member',
                display_name=display_name or name
            )
            db.session.add(member)

            # Mark invitation as accepted
            invitation.status = 'accepted'
            invitation.accepted_at = datetime.utcnow()

            db.session.commit()

            # Auto-login
            login_user(user, remember=True)

            flash(f'Welcome to {household.name}!', 'success')
            return redirect(url_for('transactions.index'))

    # GET request - show accept form
    return render_template(
        'household/accept_invite.html',
        invitation=invitation,
        household=household,
        inviter=inviter,
        token=token,
        suggested_name=None  # Could pre-fill from invitation if stored
    )
