"""
Household context helpers for managing current household in session.
"""
from flask import session
from flask_login import current_user
from models import Household, HouseholdMember


def get_current_household_id():
    """Get the current household ID from session.

    Returns:
        int: Current household ID, or None if not set
    """
    return session.get('current_household_id')


def get_current_household():
    """Get the current Household object.

    Returns:
        Household: Current household object, or None if not set
    """
    household_id = get_current_household_id()
    if household_id is None:
        return None

    return Household.query.get(household_id)


def get_current_household_members():
    """Get all members of the current household.

    Returns:
        list[HouseholdMember]: List of household member objects
    """
    household_id = get_current_household_id()
    if household_id is None:
        return []

    return HouseholdMember.query.filter_by(household_id=household_id).all()


def set_current_household(household_id):
    """Set the current household in the session.

    Args:
        household_id (int): The household ID to set as current

    Raises:
        ValueError: If user is not a member of the household
    """
    if not current_user.is_authenticated:
        raise ValueError("User must be authenticated to set household")

    # Verify user is a member of this household
    membership = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    if membership is None:
        raise ValueError("User is not a member of this household")

    session['current_household_id'] = household_id
    session.modified = True


def get_user_households():
    """Get all households the current user belongs to.

    Returns:
        list[Household]: List of households user is a member of
    """
    if not current_user.is_authenticated:
        return []

    memberships = HouseholdMember.query.filter_by(user_id=current_user.id).all()
    return [m.household for m in memberships]


def ensure_household_context():
    """Ensure a household is set in the session.

    If no household is set, automatically set to user's first household.
    If user has no households, returns False.

    Returns:
        bool: True if household context is set, False otherwise
    """
    if not current_user.is_authenticated:
        return False

    # If already set, validate it's still valid
    current_id = get_current_household_id()
    if current_id is not None:
        membership = HouseholdMember.query.filter_by(
            household_id=current_id,
            user_id=current_user.id
        ).first()
        if membership is not None:
            return True  # Valid household already set

    # No valid household set - try to set first household
    households = get_user_households()
    if not households:
        return False  # User has no households

    # Set first household as current
    set_current_household(households[0].id)
    return True


def clear_household_context():
    """Clear the current household from session."""
    session.pop('current_household_id', None)
    session.modified = True


def is_household_owner(household_id=None):
    """Check if current user is owner of the household.

    Args:
        household_id (int, optional): Household ID to check. Defaults to current household.

    Returns:
        bool: True if user is owner, False otherwise
    """
    if not current_user.is_authenticated:
        return False

    if household_id is None:
        household_id = get_current_household_id()

    if household_id is None:
        return False

    membership = HouseholdMember.query.filter_by(
        household_id=household_id,
        user_id=current_user.id
    ).first()

    return membership is not None and membership.role == 'owner'
