"""
Transaction API routes for mobile app.

Endpoints:
- GET /api/v1/transactions - List transactions (with filters)
- POST /api/v1/transactions - Create transaction
- GET /api/v1/transactions/<id> - Get single transaction
- PUT /api/v1/transactions/<id> - Update transaction
- DELETE /api/v1/transactions/<id> - Delete transaction
"""
from flask import request, jsonify, g

from models import Transaction
from api_decorators import jwt_required, api_household_required
from services.transaction_service import TransactionService
from blueprints.api_v1 import api_v1_bp


@api_v1_bp.route('/transactions', methods=['GET'])
@jwt_required
@api_household_required
def api_list_transactions():
    """List transactions for the current household.

    Query Parameters:
        month (str): Filter by month (YYYY-MM format)
        search (str): Search in merchant and notes
        date_from (str): Start date (YYYY-MM-DD)
        date_to (str): End date (YYYY-MM-DD)
        category (str): Filter by category
        paid_by (int): Filter by user ID who paid
        expense_type_id (int): Filter by expense type
        amount_min (float): Minimum amount in USD
        amount_max (float): Maximum amount in USD
        limit (int): Max number of results (default 100)
        offset (int): Offset for pagination (default 0)

    Returns:
        {
            "transactions": [...],
            "count": 50,
            "total": 150
        }
    """
    household_id = g.household_id

    # Build filters from query params
    filters = {
        'search': request.args.get('search', '').strip(),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'category': request.args.get('category'),
        'paid_by': request.args.get('paid_by', type=int),
        'expense_type_id': request.args.get('expense_type_id', type=int),
        'amount_min': request.args.get('amount_min', type=float),
        'amount_max': request.args.get('amount_max', type=float),
    }

    # Handle month filter (convert to date_from/date_to)
    month = request.args.get('month')
    if month and not filters['date_from'] and not filters['date_to']:
        # Set date range to cover the entire month
        filters['date_from'] = f"{month}-01"
        # Get last day of month
        year, mon = month.split('-')
        if mon == '12':
            next_month = f"{int(year)+1}-01"
        else:
            next_month = f"{year}-{int(mon)+1:02d}"
        from datetime import datetime, timedelta
        last_day = (datetime.strptime(f"{next_month}-01", '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        filters['date_to'] = last_day

    # Get transactions using service
    transactions = TransactionService.search_transactions(
        household_id=household_id,
        filters=filters
    )

    # Apply pagination
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    total = len(transactions)
    transactions = transactions[offset:offset + limit]

    return jsonify({
        'transactions': [txn.to_dict() for txn in transactions],
        'count': len(transactions),
        'total': total
    })


@api_v1_bp.route('/transactions', methods=['POST'])
@jwt_required
@api_household_required
def api_create_transaction():
    """Create a new transaction.

    Request body:
        {
            "date": "2024-01-15",
            "merchant": "Whole Foods",
            "amount": 85.50,
            "currency": "USD",
            "paid_by": 123,
            "category": "SHARED",
            "expense_type_id": 1,  # optional
            "notes": "Weekly groceries"  # optional
        }

    Returns:
        {"transaction": {...}}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    # Validate required fields
    required_fields = ['date', 'merchant', 'amount', 'currency', 'paid_by', 'category']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    try:
        transaction = TransactionService.create_transaction(
            household_id=g.household_id,
            data=data
        )

        return jsonify({
            'transaction': transaction.to_dict()
        }), 201

    except TransactionService.ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Failed to create transaction'}), 500


@api_v1_bp.route('/transactions/<int:transaction_id>', methods=['GET'])
@jwt_required
@api_household_required
def api_get_transaction(transaction_id):
    """Get a single transaction by ID.

    Returns:
        {"transaction": {...}}
    """
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        household_id=g.household_id
    ).first()

    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    return jsonify({
        'transaction': transaction.to_dict()
    })


@api_v1_bp.route('/transactions/<int:transaction_id>', methods=['PUT'])
@jwt_required
@api_household_required
def api_update_transaction(transaction_id):
    """Update a transaction.

    Request body (all fields optional):
        {
            "date": "2024-01-16",
            "merchant": "Trader Joe's",
            "amount": 90.00,
            "currency": "USD",
            "paid_by": 123,
            "category": "SHARED",
            "expense_type_id": 2,
            "notes": "Updated notes"
        }

    Returns:
        {"transaction": {...}}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    try:
        transaction = TransactionService.update_transaction(
            household_id=g.household_id,
            transaction_id=transaction_id,
            data=data
        )

        return jsonify({
            'transaction': transaction.to_dict()
        })

    except TransactionService.ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Failed to update transaction'}), 500


@api_v1_bp.route('/transactions/<int:transaction_id>', methods=['DELETE'])
@jwt_required
@api_household_required
def api_delete_transaction(transaction_id):
    """Delete a transaction.

    Returns:
        {"success": true}
    """
    try:
        TransactionService.delete_transaction(
            household_id=g.household_id,
            transaction_id=transaction_id
        )

        return jsonify({'success': True})

    except TransactionService.ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Failed to delete transaction'}), 500
