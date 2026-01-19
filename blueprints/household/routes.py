"""
Household management routes: create, select, switch, settings, leave.
"""
from flask import render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user

from extensions import db
from models import Household, HouseholdMember, Invitation
from decorators import household_required
from household_context import get_current_household_id, get_current_household
from blueprints.household import household_bp


@household_bp.route('/household/create', methods=['GET', 'POST'])
@login_required
def create_household():
    """Create a new household."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()

        if not name:
            flash('Household name is required.', 'danger')
            return render_template('household/setup.html')

        if not display_name:
            display_name = current_user.name

        # Create household
        household = Household(
            name=name,
            created_by_user_id=current_user.id
        )
        db.session.add(household)
        db.session.flush()  # Get household ID

        # Add creator as owner
        member = HouseholdMember(
            household_id=household.id,
            user_id=current_user.id,
            role='owner',
            display_name=display_name
        )
        db.session.add(member)
        db.session.commit()

        # Set as current household in session
        session['current_household_id'] = household.id

        flash(f'Household "{name}" created successfully!', 'success')
        return redirect(url_for('transactions.index'))

    return render_template('household/setup.html')


@household_bp.route('/household/select')
@login_required
def select_household():
    """Show household selection page."""
    households = current_user.household_memberships

    if not households:
        return redirect(url_for('household.create_household'))

    return render_template('household/select.html', households=households)


@household_bp.route('/household/switch/<int:household_id>', methods=['POST'])
@login_required
def switch_household(household_id):
    """Switch to a different household."""
    # Verify user is a member of this household
    membership = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    if not membership:
        flash('You are not a member of this household.', 'danger')
        return redirect(url_for('household.select_household'))

    # Update session
    session['current_household_id'] = household_id

    flash(f'Switched to {membership.household.name}', 'success')
    return redirect(url_for('transactions.index'))


@household_bp.route('/household/settings', methods=['GET'])
@household_required
def household_settings():
    """View household settings."""
    household_id = get_current_household_id()
    household = get_current_household()

    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    # Get current user's membership
    current_member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    is_owner = current_member and current_member.role == 'owner'

    # Get pending invitations
    pending_invitations = Invitation.query.filter_by(
        household_id=household_id,
        status='pending'
    ).all()
    pending_invitations = [inv for inv in pending_invitations if inv.is_valid()]

    return render_template(
        'household/settings.html',
        household=household,
        members=members,
        current_member=current_member,
        is_owner=is_owner,
        member_count=len(members),
        pending_invitations=pending_invitations
    )


@household_bp.route('/household/settings', methods=['POST'])
@household_required
def update_household():
    """Update household settings."""
    household_id = get_current_household_id()
    household = get_current_household()
    action = request.form.get('action')

    current_member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    is_owner = current_member and current_member.role == 'owner'

    if action == 'rename':
        if not is_owner:
            flash('Only the owner can rename the household.', 'danger')
            return redirect(url_for('household.household_settings'))

        new_name = request.form.get('name', '').strip()
        if new_name:
            household.name = new_name
            db.session.commit()
            flash('Household name updated.', 'success')

    elif action == 'update_display_name':
        new_display_name = request.form.get('display_name', '').strip()
        if new_display_name and current_member:
            current_member.display_name = new_display_name
            db.session.commit()
            flash('Your display name updated.', 'success')

    return redirect(url_for('household.household_settings'))


@household_bp.route('/household/member/<int:member_id>/remove', methods=['POST'])
@household_required
def remove_member(member_id):
    """Remove a member from the household (owner only)."""
    household_id = get_current_household_id()

    # Verify current user is owner
    current_member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    if not current_member or current_member.role != 'owner':
        flash('Only the owner can remove members.', 'danger')
        return redirect(url_for('household.household_settings'))

    # Find member to remove
    member = HouseholdMember.query.filter_by(
        id=member_id,
        household_id=household_id
    ).first_or_404()

    # Cannot remove yourself
    if member.user_id == current_user.id:
        flash('You cannot remove yourself. Use "Leave Household" instead.', 'warning')
        return redirect(url_for('household.household_settings'))

    db.session.delete(member)
    db.session.commit()

    flash(f'{member.display_name} has been removed from the household.', 'success')
    return redirect(url_for('household.household_settings'))


@household_bp.route('/household/leave', methods=['POST'])
@household_required
def leave_household():
    """Leave the current household."""
    household_id = get_current_household_id()
    household = get_current_household()

    # Find current user's membership
    member = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    if not member:
        flash('You are not a member of this household.', 'danger')
        return redirect(url_for('transactions.index'))

    # Count remaining members
    member_count = HouseholdMember.query.filter_by(household_id=household_id).count()

    if member_count == 1:
        # Last member - delete household and all data
        household_name = household.name
        db.session.delete(household)  # CASCADE deletes members, transactions, settlements
        db.session.commit()
        flash(f'Household "{household_name}" has been deleted.', 'info')
    else:
        # Just remove membership
        db.session.delete(member)
        db.session.commit()
        flash(f'You have left {household.name}.', 'info')

    # Clear session
    session.pop('current_household_id', None)

    # Check if user has other households
    if current_user.household_memberships:
        return redirect(url_for('household.select_household'))
    else:
        return redirect(url_for('household.create_household'))
