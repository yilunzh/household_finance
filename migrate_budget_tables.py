"""Database migration for budget tracking feature.

This script:
1. Creates new tables (expense_types, auto_category_rules, budget_rules, etc.)
2. Adds expense_type_id column to the existing transactions table

Run with: python migrate_budget_tables.py
"""
from app import app, db
from sqlalchemy import text


def migrate():
    with app.app_context():
        # 1. Create new tables (expense_types, etc.)
        # This is safe - it only creates tables that don't exist yet
        db.create_all()
        print("Created new tables (if they didn't exist)")

        # 2. Add expense_type_id column to transactions
        try:
            db.session.execute(text(
                'ALTER TABLE transactions ADD COLUMN expense_type_id INTEGER REFERENCES expense_types(id)'
            ))
            db.session.commit()
            print("Added expense_type_id column to transactions table")
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                print("Column expense_type_id already exists - skipping")
            else:
                print(f"Error adding column: {e}")
                raise e

        print("\nMigration complete!")
        print("\nYou can now start the app with: python app.py")


if __name__ == '__main__':
    migrate()
