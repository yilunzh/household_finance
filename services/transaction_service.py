"""
Transaction service.

Handles transaction CRUD operations and validation.
"""
from decimal import Decimal
from datetime import datetime

from extensions import db
from models import Transaction, Settlement, HouseholdMember, ExpenseType
from services.currency_service import CurrencyService


class TransactionService:
    """Service for transaction operations."""

    class ValidationError(Exception):
        """Raised when transaction validation fails."""
        pass

    @staticmethod
    def validate_paid_by(household_id, user_id):
        """
        Validate that a user belongs to the household.

        Args:
            household_id (int): The household ID
            user_id (int): The user ID

        Returns:
            HouseholdMember: The member record

        Raises:
            ValidationError: If user is not a member
        """
        member = HouseholdMember.query.filter_by(
            household_id=household_id,
            user_id=user_id
        ).first()

        if not member:
            raise TransactionService.ValidationError(
                'Invalid user selected. User is not a member of this household.'
            )

        return member

    @staticmethod
    def validate_expense_type(household_id, expense_type_id):
        """
        Validate that an expense type belongs to the household.

        Args:
            household_id (int): The household ID
            expense_type_id (int): The expense type ID

        Returns:
            ExpenseType or None: The expense type if valid, None otherwise
        """
        if not expense_type_id:
            return None

        expense_type = ExpenseType.query.filter_by(
            id=expense_type_id,
            household_id=household_id,
            is_active=True
        ).first()

        return expense_type

    @staticmethod
    def check_month_settled(household_id, month_year):
        """
        Check if a month is settled (locked).

        Args:
            household_id (int): The household ID
            month_year (str): The month in YYYY-MM format

        Returns:
            bool: True if month is settled
        """
        return Settlement.is_month_settled(household_id, month_year)

    @staticmethod
    def create_transaction(household_id, data):
        """
        Create a new transaction with validation.

        Args:
            household_id (int): The household ID
            data (dict): Transaction data containing:
                - date (str): Date in YYYY-MM-DD format
                - merchant (str): Merchant name
                - amount (float/str): Transaction amount
                - currency (str): Currency code
                - paid_by (int): User ID who paid
                - category (str): Transaction category
                - expense_type_id (int, optional): Expense type ID
                - notes (str, optional): Notes

        Returns:
            Transaction: The created transaction

        Raises:
            ValidationError: If validation fails
        """
        # Parse date
        txn_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        month_year = txn_date.strftime('%Y-%m')

        # Check if month is settled
        if TransactionService.check_month_settled(household_id, month_year):
            raise TransactionService.ValidationError(
                f'Cannot add transaction to settled month {month_year}. This month is locked.'
            )

        # Validate paid_by
        paid_by_user_id = int(data['paid_by'])
        TransactionService.validate_paid_by(household_id, paid_by_user_id)

        # Convert currency
        amount = Decimal(str(data['amount']))
        currency = data['currency']
        amount_in_usd = CurrencyService.convert_to_usd(amount, currency, txn_date)

        # Validate expense type
        expense_type_id = data.get('expense_type_id')
        if expense_type_id:
            expense_type = TransactionService.validate_expense_type(
                household_id, int(expense_type_id)
            )
            expense_type_id = expense_type.id if expense_type else None

        # Create transaction
        transaction = Transaction(
            household_id=household_id,
            date=txn_date,
            merchant=data['merchant'],
            amount=amount,
            currency=currency,
            amount_in_usd=amount_in_usd,
            paid_by_user_id=paid_by_user_id,
            category=data['category'],
            expense_type_id=expense_type_id,
            notes=data.get('notes', ''),
            month_year=month_year
        )

        db.session.add(transaction)
        db.session.commit()

        return transaction

    @staticmethod
    def update_transaction(household_id, transaction_id, data):
        """
        Update an existing transaction with validation.

        Args:
            household_id (int): The household ID
            transaction_id (int): The transaction ID
            data (dict): Fields to update

        Returns:
            Transaction: The updated transaction

        Raises:
            ValidationError: If validation fails
        """
        # Verify ownership
        transaction = Transaction.query.filter_by(
            id=transaction_id,
            household_id=household_id
        ).first()

        if not transaction:
            raise TransactionService.ValidationError('Transaction not found.')

        # Check if OLD month is settled
        if TransactionService.check_month_settled(household_id, transaction.month_year):
            raise TransactionService.ValidationError(
                f'Cannot edit transaction in settled month {transaction.month_year}. This month is locked.'
            )

        # Check if NEW month (if date changed) is settled
        if 'date' in data:
            new_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            new_month_year = new_date.strftime('%Y-%m')
            if new_month_year != transaction.month_year:
                if TransactionService.check_month_settled(household_id, new_month_year):
                    raise TransactionService.ValidationError(
                        f'Cannot move transaction to settled month {new_month_year}. That month is locked.'
                    )

        # Update fields
        if 'date' in data:
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            transaction.month_year = transaction.date.strftime('%Y-%m')

        if 'merchant' in data:
            transaction.merchant = data['merchant']

        if 'amount' in data or 'currency' in data:
            amount = Decimal(str(data.get('amount', transaction.amount)))
            currency = data.get('currency', transaction.currency)

            transaction.amount = amount
            transaction.currency = currency
            transaction.amount_in_usd = CurrencyService.convert_to_usd(
                amount, currency, transaction.date
            )

        if 'paid_by' in data:
            paid_by_user_id = int(data['paid_by'])
            TransactionService.validate_paid_by(household_id, paid_by_user_id)
            transaction.paid_by_user_id = paid_by_user_id

        if 'category' in data:
            transaction.category = data['category']

        if 'expense_type_id' in data:
            expense_type_id = data['expense_type_id']
            if expense_type_id:
                expense_type = TransactionService.validate_expense_type(
                    household_id, int(expense_type_id)
                )
                transaction.expense_type_id = expense_type.id if expense_type else None
            else:
                transaction.expense_type_id = None

        if 'notes' in data:
            transaction.notes = data['notes']

        db.session.commit()

        return transaction

    @staticmethod
    def delete_transaction(household_id, transaction_id):
        """
        Delete a transaction with validation.

        Args:
            household_id (int): The household ID
            transaction_id (int): The transaction ID

        Raises:
            ValidationError: If validation fails
        """
        # Verify ownership
        transaction = Transaction.query.filter_by(
            id=transaction_id,
            household_id=household_id
        ).first()

        if not transaction:
            raise TransactionService.ValidationError('Transaction not found.')

        # Check if month is settled
        if TransactionService.check_month_settled(household_id, transaction.month_year):
            raise TransactionService.ValidationError(
                f'Cannot delete transaction in settled month {transaction.month_year}. This month is locked.'
            )

        db.session.delete(transaction)
        db.session.commit()

    @staticmethod
    def search_transactions(household_id, filters):
        """
        Search transactions with multiple filter criteria.

        Args:
            household_id (int): The household ID
            filters (dict): Filter criteria containing:
                - search (str): Text to search in merchant and notes
                - date_from (str): Start date in YYYY-MM-DD format
                - date_to (str): End date in YYYY-MM-DD format
                - category (str): Transaction category
                - paid_by (int): User ID who paid
                - expense_type_id (int): Expense type ID
                - amount_min (float): Minimum amount in USD
                - amount_max (float): Maximum amount in USD

        Returns:
            list[Transaction]: List of matching transactions
        """
        from sqlalchemy import or_

        query = Transaction.query.filter_by(household_id=household_id)

        # Text search (phrase match in merchant OR notes)
        search_term = filters.get('search', '').strip()
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    Transaction.merchant.ilike(search_pattern),
                    Transaction.notes.ilike(search_pattern)
                )
            )

        # Date range
        date_from = filters.get('date_from')
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(Transaction.date >= from_date)
            except ValueError:
                pass  # Invalid date format, skip filter

        date_to = filters.get('date_to')
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(Transaction.date <= to_date)
            except ValueError:
                pass  # Invalid date format, skip filter

        # Category filter
        category = filters.get('category')
        if category:
            query = query.filter(Transaction.category == category)

        # Paid by filter
        paid_by = filters.get('paid_by')
        if paid_by:
            query = query.filter(Transaction.paid_by_user_id == paid_by)

        # Expense type filter
        expense_type_id = filters.get('expense_type_id')
        if expense_type_id:
            query = query.filter(Transaction.expense_type_id == expense_type_id)

        # Amount range (using USD amount)
        amount_min = filters.get('amount_min')
        if amount_min is not None:
            query = query.filter(Transaction.amount_in_usd >= amount_min)

        amount_max = filters.get('amount_max')
        if amount_max is not None:
            query = query.filter(Transaction.amount_in_usd <= amount_max)

        # Order by date desc, then created_at desc
        return query.order_by(
            Transaction.date.desc(),
            Transaction.created_at.desc()
        ).all()
