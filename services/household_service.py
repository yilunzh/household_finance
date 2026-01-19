"""
Household service.

Handles household and member management operations.
"""
from extensions import db
from models import Household, HouseholdMember, Invitation


class HouseholdService:
    """Service for household management operations."""

    class HouseholdError(Exception):
        """Raised when household operations fail."""
        pass

    @staticmethod
    def create_household(name, user_id, display_name=None):
        """
        Create a new household with the user as owner.

        Args:
            name (str): Household name
            user_id (int): Creating user's ID
            display_name (str, optional): User's display name in the household

        Returns:
            tuple: (Household, HouseholdMember) created records
        """
        household = Household(
            name=name,
            created_by_user_id=user_id
        )
        db.session.add(household)
        db.session.flush()

        member = HouseholdMember(
            household_id=household.id,
            user_id=user_id,
            role='owner',
            display_name=display_name or 'Member'
        )
        db.session.add(member)
        db.session.commit()

        return household, member

    @staticmethod
    def get_user_membership(household_id, user_id):
        """
        Get a user's membership in a household.

        Args:
            household_id (int): The household ID
            user_id (int): The user ID

        Returns:
            HouseholdMember or None
        """
        return HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=user_id
        ).first()

    @staticmethod
    def get_members(household_id):
        """
        Get all members of a household.

        Args:
            household_id (int): The household ID

        Returns:
            list: List of HouseholdMember instances
        """
        return HouseholdMember.query.filter_by(household_id=household_id).all()

    @staticmethod
    def is_owner(household_id, user_id):
        """
        Check if a user is the owner of a household.

        Args:
            household_id (int): The household ID
            user_id (int): The user ID

        Returns:
            bool: True if user is owner
        """
        member = HouseholdService.get_user_membership(household_id, user_id)
        return member and member.role == 'owner'

    @staticmethod
    def update_household_name(household_id, user_id, new_name):
        """
        Update household name (owner only).

        Args:
            household_id (int): The household ID
            user_id (int): The requesting user's ID
            new_name (str): The new name

        Raises:
            HouseholdError: If user is not owner
        """
        if not HouseholdService.is_owner(household_id, user_id):
            raise HouseholdService.HouseholdError(
                'Only the owner can rename the household.'
            )

        household = Household.query.get(household_id)
        if household:
            household.name = new_name
            db.session.commit()

    @staticmethod
    def update_display_name(household_id, user_id, new_display_name):
        """
        Update a user's display name in a household.

        Args:
            household_id (int): The household ID
            user_id (int): The user ID
            new_display_name (str): The new display name
        """
        member = HouseholdService.get_user_membership(household_id, user_id)
        if member:
            member.display_name = new_display_name
            db.session.commit()

    @staticmethod
    def remove_member(household_id, requesting_user_id, member_id):
        """
        Remove a member from the household (owner only).

        Args:
            household_id (int): The household ID
            requesting_user_id (int): The requesting user's ID
            member_id (int): The member record ID to remove

        Raises:
            HouseholdError: If operation is not allowed
        """
        if not HouseholdService.is_owner(household_id, requesting_user_id):
            raise HouseholdService.HouseholdError(
                'Only the owner can remove members.'
            )

        member = HouseholdMember.query.filter_by(
            id=member_id,
            household_id=household_id
        ).first()

        if not member:
            raise HouseholdService.HouseholdError('Member not found.')

        if member.user_id == requesting_user_id:
            raise HouseholdService.HouseholdError(
                'You cannot remove yourself. Use "Leave Household" instead.'
            )

        db.session.delete(member)
        db.session.commit()

    @staticmethod
    def leave_household(household_id, user_id):
        """
        Leave a household.

        Args:
            household_id (int): The household ID
            user_id (int): The user ID

        Returns:
            bool: True if household was deleted (last member left)

        Raises:
            HouseholdError: If user is not a member
        """
        member = HouseholdService.get_user_membership(household_id, user_id)

        if not member:
            raise HouseholdService.HouseholdError(
                'You are not a member of this household.'
            )

        member_count = HouseholdMember.query.filter_by(
            household_id=household_id
        ).count()

        if member_count == 1:
            # Last member - delete household (CASCADE deletes all data)
            household = Household.query.get(household_id)
            db.session.delete(household)
            db.session.commit()
            return True
        else:
            db.session.delete(member)
            db.session.commit()
            return False

    @staticmethod
    def get_pending_invitations(household_id):
        """
        Get valid pending invitations for a household.

        Args:
            household_id (int): The household ID

        Returns:
            list: List of valid pending Invitation instances
        """
        invitations = Invitation.query.filter_by(
            household_id=household_id,
            status='pending'
        ).all()
        return [inv for inv in invitations if inv.is_valid()]
