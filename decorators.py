"""
Custom decorators for authentication and authorization.
"""
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def household_required(f):
    """
    Decorator to require that the user belongs to a household.
    Will be fully implemented in Phase 3.

    For now, this is a placeholder that just checks if user is logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TODO: Phase 3 - Add household membership check
        # For now, just ensure user is authenticated
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def household_owner_required(f):
    """
    Decorator to require that the user is an owner of the current household.
    Will be fully implemented in Phase 6.

    For now, this is a placeholder.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TODO: Phase 6 - Add household owner check
        # For now, just ensure user is authenticated
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
