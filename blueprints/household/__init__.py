"""
Household blueprint for household management.
"""
from flask import Blueprint

household_bp = Blueprint('household', __name__)

from blueprints.household import routes  # noqa: F401, E402
