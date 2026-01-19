"""
Profile routes: user profile management, email change, password change, account deletion.
"""
import logging
import secrets
from datetime import datetime, timedelta

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, logout_user, current_user

from extensions import db, limiter
from models import User, Transaction, HouseholdMember
from blueprints.profile import profile_bp

logger = logging.getLogger(__name__)


@profile_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('profile/index.html')


@profile_bp.route('/profile/update-name', methods=['POST'])
@login_required
def profile_update_name():
    """Update user's account name."""
    name = request.form.get('name', '').strip()

    if not name:
        flash('Name cannot be empty.', 'danger')
        return redirect(url_for('profile.profile'))

    if len(name) > 100:
        flash('Name is too long (max 100 characters).', 'danger')
        return redirect(url_for('profile.profile'))

    current_user.name = name
    db.session.commit()

    flash('Your name has been updated.', 'success')
    return redirect(url_for('profile.profile'))


@profile_bp.route('/profile/request-email-change', methods=['POST'])
@login_required
@limiter.limit("3 per minute")
def profile_request_email_change():
    """Request email change - sends verification to new email."""
    new_email = request.form.get('new_email', '').strip().lower()
    password = request.form.get('password', '')

    # Validate password
    if not current_user.check_password(password):
        flash('Incorrect password.', 'danger')
        return redirect(url_for('profile.profile'))

    # Validate email format
    if not new_email or '@' not in new_email:
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('profile.profile'))

    # Check if email is same as current
    if new_email == current_user.email:
        flash('This is already your email address.', 'warning')
        return redirect(url_for('profile.profile'))

    # Check if email is already in use
    existing = User.query.filter_by(email=new_email).first()
    if existing:
        flash('This email address is already in use.', 'danger')
        return redirect(url_for('profile.profile'))

    # Generate verification token
    token = secrets.token_urlsafe(32)
    current_user.pending_email = new_email
    current_user.email_change_token = token
    current_user.email_change_expires = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    # Send verification email
    try:
        from email_service import send_email_change_verification
        send_email_change_verification(current_user, new_email, token)
    except Exception as e:
        logger.error(f"Failed to send email change verification: {e}")
        flash('Failed to send verification email. Please try again.', 'danger')
        return redirect(url_for('profile.profile'))

    return render_template('profile/email_change_sent.html', new_email=new_email)


@profile_bp.route('/profile/confirm-email/<token>')
def profile_confirm_email(token):
    """Confirm email change with token."""
    user = User.query.filter_by(email_change_token=token).first()

    if not user:
        return render_template('profile/email_invalid.html')

    if user.email_change_expires < datetime.utcnow():
        # Token expired - clear it
        user.pending_email = None
        user.email_change_token = None
        user.email_change_expires = None
        db.session.commit()
        return render_template('profile/email_invalid.html')

    # Update email
    new_email = user.pending_email
    user.email = new_email
    user.pending_email = None
    user.email_change_token = None
    user.email_change_expires = None
    db.session.commit()

    logger.info(f"Email changed for user {user.id} to {new_email}")
    flash('Your email address has been updated.', 'success')
    return render_template('profile/email_confirmed.html', new_email=new_email)


@profile_bp.route('/profile/cancel-email-change', methods=['POST'])
@login_required
def profile_cancel_email_change():
    """Cancel pending email change."""
    current_user.pending_email = None
    current_user.email_change_token = None
    current_user.email_change_expires = None
    db.session.commit()

    flash('Email change has been cancelled.', 'info')
    return redirect(url_for('profile.profile'))


@profile_bp.route('/profile/change-password', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def profile_change_password():
    """Change user's password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Validate current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile.profile'))

    # Validate new password
    if len(new_password) < 8:
        flash('New password must be at least 8 characters.', 'danger')
        return redirect(url_for('profile.profile'))

    # Confirm passwords match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('profile.profile'))

    # Update password
    current_user.set_password(new_password)
    db.session.commit()

    logger.info(f"Password changed for user: {current_user.email}")
    flash('Your password has been updated.', 'success')
    return redirect(url_for('profile.profile'))


@profile_bp.route('/profile/delete-account', methods=['POST'])
@login_required
def profile_delete_account():
    """Delete user account and anonymize transactions."""
    password = request.form.get('password', '')
    confirm_delete = request.form.get('confirm_delete', '')

    # Validate password
    if not current_user.check_password(password):
        flash('Incorrect password.', 'danger')
        return redirect(url_for('profile.profile'))

    # Require explicit confirmation
    if confirm_delete != 'DELETE':
        flash('Please type DELETE to confirm account deletion.', 'danger')
        return redirect(url_for('profile.profile'))

    user_id = current_user.id
    user_email = current_user.email

    # Anonymize transactions - set paid_by_user_id to NULL
    Transaction.query.filter_by(paid_by_user_id=user_id).update({'paid_by_user_id': None})

    # Handle household memberships
    for membership in current_user.household_memberships:
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
    db.session.delete(current_user)
    db.session.commit()

    # Logout
    logout_user()

    logger.info(f"Account deleted for user: {user_email}")
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('auth.login'))


@profile_bp.route('/api/profile/stats')
@login_required
def api_profile_stats():
    """Get user profile statistics."""
    from utils import calculate_user_stats
    stats = calculate_user_stats(current_user.id)
    return jsonify({'success': True, 'stats': stats})
