"""Database migration to add 'category' column to auto_category_rules table.

The column was added to the model in the auto-categorization feature but
db.create_all() doesn't add columns to existing tables.

Run with: python migrate_add_category_column.py
"""
from app import app, db
from sqlalchemy import text


def migrate():
    with app.app_context():
        try:
            db.session.execute(text(
                "ALTER TABLE auto_category_rules ADD COLUMN category VARCHAR(20)"
            ))
            db.session.commit()
            print("Added 'category' column to auto_category_rules table")
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                print("Column 'category' already exists - skipping")
            else:
                print(f"Error adding column: {e}")
                raise e

        print("\nMigration complete!")


if __name__ == '__main__':
    migrate()
