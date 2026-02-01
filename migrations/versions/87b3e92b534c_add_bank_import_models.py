"""Add bank import models

Revision ID: 87b3e92b534c
Revises:
Create Date: 2026-01-31 20:11:59.270116

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '87b3e92b534c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create import_sessions table
    op.create_table('import_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('household_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('source_files', sa.Text(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_sessions_household_id'), 'import_sessions', ['household_id'], unique=False)
    op.create_index(op.f('ix_import_sessions_user_id'), 'import_sessions', ['user_id'], unique=False)

    # Create extracted_transactions table
    op.create_table('extracted_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('merchant', sa.String(length=200), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('expense_type_id', sa.Integer(), nullable=True),
        sa.Column('split_category', sa.String(length=20), nullable=False),
        sa.Column('is_selected', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('flags', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['expense_type_id'], ['expense_types.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['import_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extracted_transactions_expense_type_id'), 'extracted_transactions', ['expense_type_id'], unique=False)
    op.create_index(op.f('ix_extracted_transactions_session_id'), 'extracted_transactions', ['session_id'], unique=False)

    # Create import_settings table
    op.create_table('import_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('default_currency', sa.String(length=3), nullable=False),
        sa.Column('default_split_category', sa.String(length=20), nullable=False),
        sa.Column('auto_skip_duplicates', sa.Boolean(), nullable=False),
        sa.Column('auto_select_high_confidence', sa.Boolean(), nullable=False),
        sa.Column('confidence_threshold', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_import_settings_user_id'), 'import_settings', ['user_id'], unique=True)

    # Create import_audit_logs table
    op.create_table('import_audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['import_sessions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_audit_logs_session_id'), 'import_audit_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_import_audit_logs_user_id'), 'import_audit_logs', ['user_id'], unique=False)


def downgrade():
    op.drop_table('import_audit_logs')
    op.drop_table('import_settings')
    op.drop_table('extracted_transactions')
    op.drop_table('import_sessions')
