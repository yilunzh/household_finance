"""
Invitations blueprint for household invitation management.
"""
from flask import Blueprint

invitations_bp = Blueprint('invitations', __name__)

from blueprints.invitations import routes  # noqa: F401, E402
