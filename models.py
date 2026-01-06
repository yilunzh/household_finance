"""
Database models for household expense tracker.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Transaction(db.Model):
    """Transaction model for storing expense records."""

    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False, index=True)
    merchant = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)  # USD or CAD
    amount_in_usd = db.Column(db.Numeric(10, 2), nullable=False)
    paid_by = db.Column(db.String(10), nullable=False)  # ME or WIFE
    category = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    month_year = db.Column(db.String(7), nullable=False, index=True)  # YYYY-MM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.id}: {self.merchant} ${self.amount} {self.currency}>'

    def to_dict(self):
        """Convert transaction to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'merchant': self.merchant,
            'amount': float(self.amount),
            'currency': self.currency,
            'amount_in_usd': float(self.amount_in_usd),
            'paid_by': self.paid_by,
            'category': self.category,
            'notes': self.notes,
            'month_year': self.month_year,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    @staticmethod
    def get_person_display_name(paid_by):
        """Get user-friendly person name."""
        names = {
            'ME': 'Bibi',
            'WIFE': 'Pi'
        }
        return names.get(paid_by, paid_by)

    @staticmethod
    def get_category_display_name(category):
        """Get user-friendly category name."""
        category_names = {
            'SHARED': 'Shared 50/50',
            'I_PAY_FOR_WIFE': 'Bibi pays for Pi',
            'WIFE_PAYS_FOR_ME': 'Pi pays for Bibi',
            'PERSONAL_ME': 'Personal (Bibi)',
            'PERSONAL_WIFE': 'Personal (Pi)'
        }
        return category_names.get(category, category)


class Settlement(db.Model):
    """Settlement model for recording monthly settlement snapshots."""

    __tablename__ = 'settlements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    month_year = db.Column(db.String(7), nullable=False, unique=True, index=True)  # YYYY-MM, UNIQUE!
    settled_date = db.Column(db.Date, nullable=False)  # When marked as settled
    settlement_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Absolute amount owed
    from_person = db.Column(db.String(10), nullable=False)  # ME or WIFE (who owes)
    to_person = db.Column(db.String(10), nullable=False)  # ME or WIFE (who is owed)
    settlement_message = db.Column(db.String(200), nullable=False)  # "Pi owes Bibi $50.00"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Settlement {self.month_year}: {self.settlement_message}>'

    def to_dict(self):
        """Convert settlement to dictionary for JSON."""
        return {
            'id': self.id,
            'month_year': self.month_year,
            'settled_date': self.settled_date.strftime('%Y-%m-%d'),
            'settlement_amount': float(self.settlement_amount),
            'from_person': self.from_person,
            'to_person': self.to_person,
            'settlement_message': self.settlement_message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    @staticmethod
    def is_month_settled(month_year):
        """Check if a month has been settled."""
        return Settlement.query.filter_by(month_year=month_year).first() is not None

    @staticmethod
    def get_settlement(month_year):
        """Get settlement record for a month."""
        return Settlement.query.filter_by(month_year=month_year).first()
