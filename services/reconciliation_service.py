"""
Reconciliation service.

Handles settlement calculations and recording.
"""
from decimal import Decimal
from datetime import datetime

from extensions import db
from models import Transaction, Settlement, BudgetRule, BudgetSnapshot
from utils import calculate_reconciliation, build_split_rules_lookup
from budget_utils import create_or_update_budget_snapshot


class ReconciliationService:
    """Service for reconciliation and settlement operations."""

    class SettlementError(Exception):
        """Raised when settlement operations fail."""
        pass

    @staticmethod
    def get_monthly_summary(household_id, household_members, month_year, budget_data=None):
        """
        Calculate reconciliation summary for a month.

        Args:
            household_id (int): The household ID
            household_members (list): List of HouseholdMember instances
            month_year (str): Month in YYYY-MM format
            budget_data (list, optional): Budget data for the month

        Returns:
            dict: Reconciliation summary
        """
        transactions = Transaction.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).all()

        if not transactions:
            return None

        split_rules_lookup = build_split_rules_lookup(household_id)
        return calculate_reconciliation(
            transactions, household_members, budget_data, split_rules_lookup
        )

    @staticmethod
    def create_settlement(household_id, household_members, month_year):
        """
        Create a settlement record for a month.

        Args:
            household_id (int): The household ID
            household_members (list): List of HouseholdMember instances
            month_year (str): Month in YYYY-MM format

        Returns:
            Settlement: The created settlement record

        Raises:
            SettlementError: If settlement cannot be created
        """
        # Check if already settled
        if Settlement.is_month_settled(household_id, month_year):
            raise ReconciliationService.SettlementError(
                'This month has already been settled.'
            )

        # Get transactions
        transactions = Transaction.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).all()

        if not transactions:
            raise ReconciliationService.SettlementError(
                'Cannot settle a month with no transactions.'
            )

        # Calculate reconciliation
        split_rules_lookup = build_split_rules_lookup(household_id)
        summary = calculate_reconciliation(transactions, household_members, None, split_rules_lookup)

        # Extract balances
        user_balances = summary.get('user_balances', {})

        if len(user_balances) != 2:
            raise ReconciliationService.SettlementError(
                'Settlement currently only supports 2-person households.'
            )

        # Determine settlement direction
        user_ids = list(user_balances.keys())
        user1_id = user_ids[0]
        user2_id = user_ids[1]
        user1_balance = Decimal(str(user_balances[user1_id]))
        user2_balance = Decimal(str(user_balances[user2_id]))

        if user1_balance > Decimal('0.01'):
            from_user_id, to_user_id, settlement_amount = user2_id, user1_id, user1_balance
        elif user2_balance > Decimal('0.01'):
            from_user_id, to_user_id, settlement_amount = user1_id, user2_id, user2_balance
        else:
            from_user_id, to_user_id, settlement_amount = user1_id, user2_id, Decimal('0.00')

        # Create settlement record
        settlement = Settlement(
            household_id=household_id,
            month_year=month_year,
            settled_date=datetime.now().date(),
            settlement_amount=settlement_amount,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            settlement_message=summary['settlement']
        )

        db.session.add(settlement)

        # Create budget snapshots
        budget_rules = BudgetRule.query.filter_by(
            household_id=household_id,
            is_active=True
        ).all()

        for budget_rule in budget_rules:
            create_or_update_budget_snapshot(budget_rule, month_year, finalize=True)

        db.session.commit()

        return settlement

    @staticmethod
    def remove_settlement(household_id, month_year):
        """
        Remove a settlement to unlock a month.

        Args:
            household_id (int): The household ID
            month_year (str): Month in YYYY-MM format

        Raises:
            SettlementError: If settlement doesn't exist
        """
        settlement = Settlement.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).first()

        if not settlement:
            raise ReconciliationService.SettlementError(
                'This month is not settled.'
            )

        db.session.delete(settlement)

        # Unfinalize budget snapshots
        budget_rules = BudgetRule.query.filter_by(
            household_id=household_id,
            is_active=True
        ).all()

        for budget_rule in budget_rules:
            snapshot = BudgetSnapshot.query.filter_by(
                budget_rule_id=budget_rule.id,
                month_year=month_year
            ).first()
            if snapshot:
                snapshot.is_finalized = False

        db.session.commit()
