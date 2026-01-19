"""
API blueprint for REST API endpoints.
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from blueprints.api import routes  # noqa: F401, E402
