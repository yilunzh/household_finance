"""
Flask-Login authentication configuration.
"""
from flask_login import LoginManager
from models import db, User

# Create LoginManager instance
login_manager = LoginManager()

# Configure login view
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access this page.'


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
