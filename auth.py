"""
Flask-Login authentication configuration.
"""
from models import User
from extensions import login_manager


@login_manager.user_loader
def load_user(user_id):
    """
    User loader callback for Flask-Login.
    Loads a user from the database by user ID.

    Args:
        user_id: The ID of the user to load

    Returns:
        User object if found, None otherwise
    """
    return User.query.get(int(user_id))
