"""
Profile blueprint for user profile management.
"""
from flask import Blueprint

profile_bp = Blueprint('profile', __name__)

from blueprints.profile import routes  # noqa: F401, E402
