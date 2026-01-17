"""
Database models for household expense tracker.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """User model for authentication."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(64), unique=True, nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)

    # Relationships
    household_memberships = db.relationship('HouseholdMember', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set the user's password."""
        # Use pbkdf2:sha256 explicitly for Python 3.9 compatibility
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.id}: {self.email}>'


class Household(db.Model):
    """Household model for multi-tenancy."""

    __tablename__ = 'households'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_user_id])
    members = db.relationship('HouseholdMember', back_populates='household', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', back_populates='household', cascade='all, delete-orphan')
    settlements = db.relationship('Settlement', back_populates='household', cascade='all, delete-orphan')
    invitations = db.relationship('Invitation', back_populates='household', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Household {self.id}: {self.name}>'


class HouseholdMember(db.Model):
    """Association table for users belonging to households."""

    __tablename__ = 'household_members'
    __table_args__ = (
        db.UniqueConstraint('household_id', 'user_id', name='unique_household_user'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # 'owner' or 'member'
    display_name = db.Column(db.String(50), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    household = db.relationship('Household', back_populates='members')
    user = db.relationship('User', back_populates='household_memberships')

    def __repr__(self):
        return f'<HouseholdMember {self.id}: User {self.user_id} in Household {self.household_id}>'


class Invitation(db.Model):
    """Invitation model for inviting users to households."""

    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'accepted', 'expired'
    expires_at = db.Column(db.DateTime, nullable=False)
    invited_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    household = db.relationship('Household', back_populates='invitations')
    invited_by = db.relationship('User', foreign_keys=[invited_by_user_id])

    def is_valid(self):
        """Check if invitation is still valid."""
        return self.status == 'pending' and self.expires_at > datetime.utcnow()

    def __repr__(self):
        return f'<Invitation {self.id}: {self.email} to Household {self.household_id}>'


class Transaction(db.Model):
    """Transaction model for storing expense records."""

    __tablename__ = 'transactions'
    __table_args__ = (
        db.Index('idx_household_month', 'household_id', 'month_year'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    merchant = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)  # USD or CAD
    amount_in_usd = db.Column(db.Numeric(10, 2), nullable=False)
    paid_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category = db.Column(db.String(20), nullable=False)
    expense_type_id = db.Column(db.Integer, db.ForeignKey('expense_types.id'), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    month_year = db.Column(db.String(7), nullable=False, index=True)  # YYYY-MM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    household = db.relationship('Household', back_populates='transactions')
    paid_by_user = db.relationship('User')
    expense_type = db.relationship('ExpenseType', backref='transactions')

    def __repr__(self):
        return f'<Transaction {self.id}: {self.merchant} ${self.amount} {self.currency}>'

    def to_dict(self):
        """Convert transaction to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'household_id': self.household_id,
            'date': self.date.strftime('%Y-%m-%d'),
            'merchant': self.merchant,
            'amount': float(self.amount),
            'currency': self.currency,
            'amount_in_usd': float(self.amount_in_usd),
            'paid_by_user_id': self.paid_by_user_id,
            'paid_by_name': self.get_paid_by_display_name(),
            'category': self.category,
            'expense_type_id': self.expense_type_id,
            'expense_type_name': self.expense_type.name if self.expense_type else None,
            'notes': self.notes,
            'month_year': self.month_year,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def get_paid_by_display_name(self):
        """Get display name for the user who paid."""
        member = HouseholdMember.query.filter_by(
            household_id=self.household_id,
            user_id=self.paid_by_user_id
        ).first()
        return member.display_name if member else "Unknown"

    @staticmethod
    def get_category_display_name(category, household_members=None):
        """Get user-friendly category name.

        Args:
            category: Category code (SHARED, I_PAY_FOR_WIFE, etc.)
            household_members: Optional list of HouseholdMember objects for dynamic names
        """
        if household_members and len(household_members) >= 2:
            name1 = household_members[0].display_name
            name2 = household_members[1].display_name
            category_names = {
                'SHARED': 'Shared 50/50',
                'I_PAY_FOR_WIFE': f'For {name2} (by {name1})',
                'WIFE_PAYS_FOR_ME': f'For {name1} (by {name2})',
                'PERSONAL_ME': f'Personal ({name1})',
                'PERSONAL_WIFE': f'Personal ({name2})'
            }
        else:
            # Fallback when members not provided
            category_names = {
                'SHARED': 'Shared 50/50',
                'I_PAY_FOR_WIFE': 'For partner (by me)',
                'WIFE_PAYS_FOR_ME': 'For me (by partner)',
                'PERSONAL_ME': 'Personal',
                'PERSONAL_WIFE': 'Personal (partner)'
            }
        return category_names.get(category, category)


class Settlement(db.Model):
    """Settlement model for recording monthly settlement snapshots."""

    __tablename__ = 'settlements'
    __table_args__ = (
        db.UniqueConstraint('household_id', 'month_year', name='unique_household_month_settlement'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    month_year = db.Column(db.String(7), nullable=False, index=True)  # YYYY-MM
    settled_date = db.Column(db.Date, nullable=False)  # When marked as settled
    settlement_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Absolute amount owed
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Who owes
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Who is owed
    settlement_message = db.Column(db.String(200), nullable=False)  # "Member 2 owes Member 1 $50.00"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    household = db.relationship('Household', back_populates='settlements')
    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])

    def __repr__(self):
        return f'<Settlement {self.month_year}: {self.settlement_message}>'

    def to_dict(self):
        """Convert settlement to dictionary for JSON."""
        return {
            'id': self.id,
            'household_id': self.household_id,
            'month_year': self.month_year,
            'settled_date': self.settled_date.strftime('%Y-%m-%d'),
            'settlement_amount': float(self.settlement_amount),
            'from_user_id': self.from_user_id,
            'to_user_id': self.to_user_id,
            'settlement_message': self.settlement_message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    @staticmethod
    def is_month_settled(household_id, month_year):
        """Check if a month has been settled for a household."""
        return Settlement.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).first() is not None

    @staticmethod
    def get_settlement(household_id, month_year):
        """Get settlement record for a household month."""
        return Settlement.query.filter_by(
            household_id=household_id,
            month_year=month_year
        ).first()


class ExpenseType(db.Model):
    """Expense type categories (per household)."""

    __tablename__ = 'expense_types'
    __table_args__ = (
        db.UniqueConstraint('household_id', 'name', name='unique_household_expense_type'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Grocery", "Dining", "Household"
    icon = db.Column(db.String(50), nullable=True)   # Optional icon identifier
    color = db.Column(db.String(20), nullable=True)  # Optional color for UI (e.g., "terracotta", "sage")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    household = db.relationship('Household', backref='expense_types')

    def __repr__(self):
        return f'<ExpenseType {self.id}: {self.name}>'

    def to_dict(self):
        """Convert expense type to dictionary for JSON."""
        return {
            'id': self.id,
            'household_id': self.household_id,
            'name': self.name,
            'icon': self.icon,
            'color': self.color,
            'is_active': self.is_active
        }


class AutoCategoryRule(db.Model):
    """Rules for auto-categorizing transactions by merchant keywords."""

    __tablename__ = 'auto_category_rules'
    __table_args__ = (
        db.Index('idx_household_keyword', 'household_id', 'keyword'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    keyword = db.Column(db.String(100), nullable=False)  # Case-insensitive match
    expense_type_id = db.Column(db.Integer, db.ForeignKey('expense_types.id'), nullable=False)
    priority = db.Column(db.Integer, default=0)  # Higher = checked first
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    household = db.relationship('Household', backref='auto_category_rules')
    expense_type = db.relationship('ExpenseType', backref='auto_rules')

    def __repr__(self):
        return f'<AutoCategoryRule {self.id}: "{self.keyword}" -> {self.expense_type_id}>'

    def to_dict(self):
        """Convert auto category rule to dictionary for JSON."""
        return {
            'id': self.id,
            'household_id': self.household_id,
            'keyword': self.keyword,
            'expense_type_id': self.expense_type_id,
            'expense_type_name': self.expense_type.name if self.expense_type else None,
            'priority': self.priority
        }


class BudgetRule(db.Model):
    """Budget allocation rule: who gives whom how much for which expense types."""

    __tablename__ = 'budget_rules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    giver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Who provides budget
    receiver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Who receives/manages budget
    monthly_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Monthly budget in USD
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    household = db.relationship('Household', backref='budget_rules')
    giver = db.relationship('User', foreign_keys=[giver_user_id])
    receiver = db.relationship('User', foreign_keys=[receiver_user_id])
    expense_types = db.relationship('BudgetRuleExpenseType', back_populates='budget_rule', cascade='all, delete-orphan')
    snapshots = db.relationship('BudgetSnapshot', back_populates='budget_rule', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BudgetRule {self.id}: ${self.monthly_amount}/month>'

    def get_giver_display_name(self):
        """Get display name for the budget giver."""
        member = HouseholdMember.query.filter_by(
            household_id=self.household_id,
            user_id=self.giver_user_id
        ).first()
        return member.display_name if member else "Unknown"

    def get_receiver_display_name(self):
        """Get display name for the budget receiver."""
        member = HouseholdMember.query.filter_by(
            household_id=self.household_id,
            user_id=self.receiver_user_id
        ).first()
        return member.display_name if member else "Unknown"

    def get_expense_type_ids(self):
        """Get list of expense type IDs for this rule."""
        return [et.expense_type_id for et in self.expense_types]

    def get_expense_type_names(self):
        """Get list of expense type names for this rule."""
        return [et.expense_type.name for et in self.expense_types if et.expense_type]

    def to_dict(self):
        """Convert budget rule to dictionary for JSON."""
        return {
            'id': self.id,
            'household_id': self.household_id,
            'giver_user_id': self.giver_user_id,
            'giver_name': self.get_giver_display_name(),
            'receiver_user_id': self.receiver_user_id,
            'receiver_name': self.get_receiver_display_name(),
            'monthly_amount': float(self.monthly_amount),
            'expense_type_ids': self.get_expense_type_ids(),
            'expense_type_names': self.get_expense_type_names(),
            'is_active': self.is_active
        }


class BudgetRuleExpenseType(db.Model):
    """Association table for budget rules and expense types (many-to-many)."""

    __tablename__ = 'budget_rule_expense_types'
    __table_args__ = (
        db.UniqueConstraint('budget_rule_id', 'expense_type_id', name='unique_rule_expense_type'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    budget_rule_id = db.Column(db.Integer, db.ForeignKey('budget_rules.id'), nullable=False, index=True)
    expense_type_id = db.Column(db.Integer, db.ForeignKey('expense_types.id'), nullable=False, index=True)

    budget_rule = db.relationship('BudgetRule', back_populates='expense_types')
    expense_type = db.relationship('ExpenseType')

    def __repr__(self):
        return f'<BudgetRuleExpenseType: Rule {self.budget_rule_id} -> Type {self.expense_type_id}>'


class BudgetSnapshot(db.Model):
    """Monthly budget status snapshot for tracking cumulative over/under."""

    __tablename__ = 'budget_snapshots'
    __table_args__ = (
        db.UniqueConstraint('budget_rule_id', 'month_year', name='unique_budget_rule_month'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    budget_rule_id = db.Column(db.Integer, db.ForeignKey('budget_rules.id'), nullable=False, index=True)
    month_year = db.Column(db.String(7), nullable=False, index=True)  # YYYY-MM
    budget_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Budget for this month
    spent_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Actual spending
    giver_reimbursement = db.Column(db.Numeric(10, 2), default=0)  # Amount giver paid that should be reimbursed
    carryover_from_previous = db.Column(db.Numeric(10, 2), default=0)  # + = surplus, - = deficit
    net_balance = db.Column(db.Numeric(10, 2), nullable=False)  # Final balance after all calculations
    is_finalized = db.Column(db.Boolean, default=False)  # Locked when month is settled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    budget_rule = db.relationship('BudgetRule', back_populates='snapshots')

    def __repr__(self):
        return f'<BudgetSnapshot {self.month_year}: ${self.spent_amount}/${self.budget_amount}>'

    def to_dict(self):
        """Convert budget snapshot to dictionary for JSON."""
        return {
            'id': self.id,
            'budget_rule_id': self.budget_rule_id,
            'month_year': self.month_year,
            'budget_amount': float(self.budget_amount),
            'spent_amount': float(self.spent_amount),
            'giver_reimbursement': float(self.giver_reimbursement),
            'carryover_from_previous': float(self.carryover_from_previous),
            'net_balance': float(self.net_balance),
            'is_finalized': self.is_finalized
        }
