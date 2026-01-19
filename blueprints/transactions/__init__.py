"""
Transactions blueprint for transaction CRUD operations.
"""
from flask import Blueprint

transactions_bp = Blueprint('transactions', __name__)

from blueprints.transactions import routes  # noqa: F401, E402
