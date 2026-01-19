"""
Transaction API routes for mobile app.

Endpoints:
- GET /api/v1/transactions - List transactions (with filters)
- POST /api/v1/transactions - Create transaction
- GET /api/v1/transactions/<id> - Get single transaction
- PUT /api/v1/transactions/<id> - Update transaction
- DELETE /api/v1/transactions/<id> - Delete transaction
- POST /api/v1/transactions/<id>/receipt - Upload receipt image
- DELETE /api/v1/transactions/<id>/receipt - Delete receipt image
"""
import os
import uuid
from flask import request, jsonify, g, current_app, send_from_directory
from werkzeug.utils import secure_filename

from models import Transaction
from extensions import db
from api_decorators import jwt_required, api_household_required
from services.transaction_service import TransactionService
from blueprints.api_v1 import api_v1_bp

# Allowed file extensions for receipts
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_upload_folder():
    """Get the upload folder path, creating it if needed."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads/receipts')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


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


@api_v1_bp.route('/transactions/<int:transaction_id>/receipt', methods=['POST'])
@jwt_required
@api_household_required
def api_upload_receipt(transaction_id):
    """Upload a receipt image for a transaction.

    Request: multipart/form-data with 'file' field containing the image.

    Returns:
        {"transaction": {...}, "receipt_url": "..."}
    """
    # Find the transaction
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        household_id=g.household_id
    ).first()

    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': f'File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB'}), 400

    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{g.household_id}_{transaction_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filename = secure_filename(filename)

    # Delete old receipt if exists
    if transaction.receipt_url:
        old_path = os.path.join(get_upload_folder(), os.path.basename(transaction.receipt_url))
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save file
    upload_folder = get_upload_folder()
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    # Update transaction with receipt URL
    transaction.receipt_url = f"/api/v1/receipts/{filename}"
    db.session.commit()

    return jsonify({
        'transaction': transaction.to_dict(),
        'receipt_url': transaction.receipt_url
    })


@api_v1_bp.route('/transactions/<int:transaction_id>/receipt', methods=['DELETE'])
@jwt_required
@api_household_required
def api_delete_receipt(transaction_id):
    """Delete a receipt image from a transaction.

    Returns:
        {"transaction": {...}}
    """
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        household_id=g.household_id
    ).first()

    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    if not transaction.receipt_url:
        return jsonify({'error': 'No receipt to delete'}), 400

    # Delete file from disk
    filename = os.path.basename(transaction.receipt_url)
    file_path = os.path.join(get_upload_folder(), filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Clear receipt URL
    transaction.receipt_url = None
    db.session.commit()

    return jsonify({
        'transaction': transaction.to_dict()
    })


@api_v1_bp.route('/receipts/<filename>', methods=['GET'])
def api_get_receipt(filename):
    """Serve a receipt image.

    Note: No auth required for serving images - filenames are unguessable UUIDs.
    In production, consider using a CDN or cloud storage with signed URLs.
    """
    # Security: ensure filename is safe
    filename = secure_filename(filename)
    upload_folder = get_upload_folder()

    # Check if file exists
    file_path = os.path.join(upload_folder, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Receipt not found'}), 404

    return send_from_directory(upload_folder, filename)
