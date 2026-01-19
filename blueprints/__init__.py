"""
Flask blueprints for organizing routes by domain.

Blueprints are imported and registered incrementally as they are extracted.
"""
from blueprints.auth import auth_bp

# TODO: Add these as they are extracted from app.py
# from blueprints.profile import profile_bp
# from blueprints.household import household_bp
# from blueprints.invitations import invitations_bp
# from blueprints.transactions import transactions_bp
# from blueprints.reconciliation import reconciliation_bp
# from blueprints.budget import budget_bp
# from blueprints.api import api_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(auth_bp)
    # TODO: Register these as they are extracted
    # app.register_blueprint(profile_bp)
    # app.register_blueprint(household_bp)
    # app.register_blueprint(invitations_bp)
    # app.register_blueprint(transactions_bp)
    # app.register_blueprint(reconciliation_bp)
    # app.register_blueprint(budget_bp)
    # app.register_blueprint(api_bp)
