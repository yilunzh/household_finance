"""
API v1 Blueprint for mobile app.

Provides REST API endpoints with JWT authentication for the iOS/Android apps.
"""
from flask import Blueprint

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Import routes to register them with the blueprint
from blueprints.api_v1 import auth  # noqa: F401, E402
from blueprints.api_v1 import transactions  # noqa: F401, E402
from blueprints.api_v1 import households  # noqa: F401, E402
from blueprints.api_v1 import reconciliation  # noqa: F401, E402
from blueprints.api_v1 import config  # noqa: F401, E402
