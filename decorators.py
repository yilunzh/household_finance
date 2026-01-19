"""
Custom decorators for authentication and authorization.
"""
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from household_context import ensure_household_context, is_household_owner


def household_required(f):
    """Decorator to require that the user belongs to a household.

    Ensures:
    1. User is authenticated
    2. User has a household set in session
    3. If no household, redirects to household setup
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # Ensure household context is set
        if not ensure_household_context():
            # User has no households - redirect to setup
            flash('Please create or join a household first.', 'info')
            return redirect(url_for('household.create_household'))

        return f(*args, **kwargs)
    return decorated_function


def household_owner_required(f):
    """Decorator to require that the user is an owner of the current household.

    Ensures:
    1. User is authenticated
    2. User has a household set in session
    3. User is an owner (not just a member) of the household
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # Ensure household context is set
        if not ensure_household_context():
            flash('Please create or join a household first.', 'info')
            return redirect(url_for('household.create_household'))

        # Check if user is owner
        if not is_household_owner():
            flash('You must be a household owner to access this page.', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function
