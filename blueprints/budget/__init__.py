"""
Budget blueprint for budget tracking page.
"""
from flask import Blueprint

budget_bp = Blueprint('budget', __name__)

from blueprints.budget import routes  # noqa: F401, E402
