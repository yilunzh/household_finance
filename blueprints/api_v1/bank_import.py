"""
Bank Import API routes for mobile app.

Endpoints:
- POST /api/v1/import/sessions - Create import session (upload files)
- GET /api/v1/import/sessions - List user's import sessions
- GET /api/v1/import/sessions/<id> - Get session status
- DELETE /api/v1/import/sessions/<id> - Delete session
- GET /api/v1/import/sessions/<id>/transactions - List extracted transactions
- PUT /api/v1/import/sessions/<id>/transactions/<tid> - Update transaction
- POST /api/v1/import/sessions/<id>/import - Finalize import
- GET /api/v1/import/rules - List auto-categorization rules
- POST /api/v1/import/rules - Create rule
- PUT /api/v1/import/rules/<id> - Update rule
- DELETE /api/v1/import/rules/<id> - Delete rule
- GET /api/v1/import/settings - Get user's import settings
- PUT /api/v1/import/settings - Update import settings
"""
import json
from concurrent.futures import ThreadPoolExecutor
from flask import request, jsonify, g

from extensions import db
from models import ImportSession, ExtractedTransaction, ImportSettings, AutoCategoryRule, ExpenseType
from api_decorators import jwt_required, api_household_required
from services.import_service import ImportService
from blueprints.api_v1 import api_v1_bp

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=2)


# =============================================================================
# Session Endpoints
# =============================================================================

@api_v1_bp.route('/import/sessions', methods=['POST'])
@jwt_required
@api_household_required
def api_create_import_session():
    """Create a new import session by uploading files.

    Request: multipart/form-data with 'files' field(s) containing bank statements.

    Returns:
        {
            "session": {...},
            "message": "Processing started"
        }
    """
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    # Get files from either 'files' (multiple) or 'file' (single)
    files = request.files.getlist('files')
    if not files or (len(files) == 1 and not files[0].filename):
        files = request.files.getlist('file')

    if not files or (len(files) == 1 and not files[0].filename):
        return jsonify({'error': 'No files provided'}), 400

    try:
        session = ImportService.create_session(
            user_id=g.current_user_id,
            household_id=g.household_id,
            files=files
        )

        # Start background processing
        from app import app
        def process_with_context(session_id):
            with app.app_context():
                ImportService.process_session(session_id)

        executor.submit(process_with_context, session.id)

        return jsonify({
            'session': session.to_dict(),
            'message': 'Processing started'
        }), 201

    except ImportService.ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to create import session: {str(e)}'}), 500


@api_v1_bp.route('/import/sessions', methods=['GET'])
@jwt_required
def api_list_import_sessions():
    """List user's import sessions.

    Query Parameters:
        status (str): Filter by status
        limit (int): Max results (default 20)
        offset (int): Pagination offset (default 0)

    Returns:
        {
            "sessions": [...],
            "count": 5,
            "total": 10
        }
    """
    query = ImportSession.query.filter_by(user_id=g.current_user_id)

    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    # Order by created_at descending
    query = query.order_by(ImportSession.created_at.desc())

    # Get total count
    total = query.count()

    # Pagination
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    sessions = query.offset(offset).limit(limit).all()

    return jsonify({
        'sessions': [s.to_dict() for s in sessions],
        'count': len(sessions),
        'total': total
    })


@api_v1_bp.route('/import/sessions/<int:session_id>', methods=['GET'])
@jwt_required
def api_get_import_session(session_id):
    """Get import session status and details.

    Returns:
        {"session": {...}}
    """
    session = ImportService.get_session(session_id, g.current_user_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({
        'session': session.to_dict()
    })


@api_v1_bp.route('/import/sessions/<int:session_id>', methods=['DELETE'])
@jwt_required
def api_delete_import_session(session_id):
    """Delete an import session and its files.

    Returns:
        {"success": true}
    """
    try:
        ImportService.delete_session(session_id, g.current_user_id)
        return jsonify({'success': True})

    except ImportService.ValidationError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to delete session: {str(e)}'}), 500


# =============================================================================
# Transaction Endpoints
# =============================================================================

@api_v1_bp.route('/import/sessions/<int:session_id>/transactions', methods=['GET'])
@jwt_required
def api_list_session_transactions(session_id):
    """List extracted transactions for a session.

    Query Parameters:
        status (str): Filter by status (pending, reviewed, imported, skipped)
        is_selected (bool): Filter by selection status
        needs_review (bool): Filter to only items needing review

    Returns:
        {
            "transactions": [...],
            "count": 10
        }
    """
    filters = {
        'status': request.args.get('status'),
        'is_selected': request.args.get('is_selected', type=lambda x: x.lower() == 'true')
    }

    transactions = ImportService.get_session_transactions(
        session_id, g.current_user_id, filters
    )

    if transactions is None:
        return jsonify({'error': 'Session not found'}), 404

    # Post-filter for needs_review if specified
    needs_review = request.args.get('needs_review')
    if needs_review is not None:
        needs_review = needs_review.lower() == 'true'
        transactions = [t for t in transactions if t.needs_review() == needs_review]

    return jsonify({
        'transactions': [t.to_dict() for t in transactions],
        'count': len(transactions)
    })


@api_v1_bp.route('/import/sessions/<int:session_id>/transactions/<int:transaction_id>', methods=['PUT'])
@jwt_required
def api_update_session_transaction(session_id, transaction_id):
    """Update an extracted transaction.

    Request body (all fields optional):
        {
            "merchant": "Updated Merchant",
            "amount": 100.00,
            "date": "2024-01-15",
            "expense_type_id": 1,
            "split_category": "SHARED",
            "is_selected": true
        }

    Returns:
        {"transaction": {...}}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    try:
        transaction = ImportService.update_transaction(
            session_id, transaction_id, g.current_user_id, data
        )
        return jsonify({
            'transaction': transaction.to_dict()
        })

    except ImportService.ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update transaction: {str(e)}'}), 500


@api_v1_bp.route('/import/sessions/<int:session_id>/import', methods=['POST'])
@jwt_required
def api_import_session_transactions(session_id):
    """Import selected transactions into the main transaction table.

    Request body (optional):
        {
            "transaction_ids": [1, 2, 3]  // Optional: specific transactions to import
        }

    Returns:
        {
            "success": true,
            "imported_count": 5
        }
    """
    data = request.get_json() or {}
    transaction_ids = data.get('transaction_ids')

    try:
        imported_count = ImportService.import_transactions(
            session_id, g.current_user_id, transaction_ids
        )

        return jsonify({
            'success': True,
            'imported_count': imported_count
        })

    except ImportService.ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to import transactions: {str(e)}'}), 500


# =============================================================================
# Rules Endpoints
# =============================================================================

@api_v1_bp.route('/import/rules', methods=['GET'])
@jwt_required
@api_household_required
def api_list_import_rules():
    """List auto-categorization rules for the household.

    Returns:
        {
            "rules": [...],
            "count": 5
        }
    """
    rules = AutoCategoryRule.query.filter_by(
        household_id=g.household_id
    ).order_by(AutoCategoryRule.keyword).all()

    return jsonify({
        'rules': [r.to_dict() for r in rules],
        'count': len(rules)
    })


@api_v1_bp.route('/import/rules', methods=['POST'])
@jwt_required
@api_household_required
def api_create_import_rule():
    """Create a new auto-categorization rule.

    Request body:
        {
            "keyword": "whole foods",
            "expense_type_id": 1
        }

    Returns:
        {"rule": {...}}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    # Validate required fields
    if not data.get('keyword'):
        return jsonify({'error': 'keyword is required'}), 400
    if not data.get('expense_type_id'):
        return jsonify({'error': 'expense_type_id is required'}), 400

    # Validate expense type belongs to household
    expense_type = ExpenseType.query.filter_by(
        id=data['expense_type_id'],
        household_id=g.household_id
    ).first()

    if not expense_type:
        return jsonify({'error': 'Invalid expense type'}), 400

    # Check for duplicate keyword
    keyword = data['keyword'].strip().lower()
    existing = AutoCategoryRule.query.filter_by(
        household_id=g.household_id
    ).filter(
        db.func.lower(AutoCategoryRule.keyword) == keyword
    ).first()

    if existing:
        return jsonify({'error': 'A rule with this keyword already exists'}), 400

    # Create rule
    rule = AutoCategoryRule(
        household_id=g.household_id,
        keyword=data['keyword'].strip(),
        expense_type_id=data['expense_type_id']
    )
    db.session.add(rule)
    db.session.commit()

    return jsonify({
        'rule': rule.to_dict()
    }), 201


@api_v1_bp.route('/import/rules/<int:rule_id>', methods=['PUT'])
@jwt_required
@api_household_required
def api_update_import_rule(rule_id):
    """Update an auto-categorization rule.

    Request body:
        {
            "keyword": "updated keyword",
            "expense_type_id": 2
        }

    Returns:
        {"rule": {...}}
    """
    rule = AutoCategoryRule.query.filter_by(
        id=rule_id,
        household_id=g.household_id
    ).first()

    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    # Update keyword
    if 'keyword' in data:
        keyword = data['keyword'].strip().lower()
        # Check for duplicate
        existing = AutoCategoryRule.query.filter_by(
            household_id=g.household_id
        ).filter(
            db.func.lower(AutoCategoryRule.keyword) == keyword,
            AutoCategoryRule.id != rule_id
        ).first()

        if existing:
            return jsonify({'error': 'A rule with this keyword already exists'}), 400

        rule.keyword = data['keyword'].strip()

    # Update expense type
    if 'expense_type_id' in data:
        expense_type = ExpenseType.query.filter_by(
            id=data['expense_type_id'],
            household_id=g.household_id
        ).first()

        if not expense_type:
            return jsonify({'error': 'Invalid expense type'}), 400

        rule.expense_type_id = data['expense_type_id']

    db.session.commit()

    return jsonify({
        'rule': rule.to_dict()
    })


@api_v1_bp.route('/import/rules/<int:rule_id>', methods=['DELETE'])
@jwt_required
@api_household_required
def api_delete_import_rule(rule_id):
    """Delete an auto-categorization rule.

    Returns:
        204 No Content
    """
    rule = AutoCategoryRule.query.filter_by(
        id=rule_id,
        household_id=g.household_id
    ).first()

    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    db.session.delete(rule)
    db.session.commit()

    return '', 204


# =============================================================================
# Settings Endpoints
# =============================================================================

@api_v1_bp.route('/import/settings', methods=['GET'])
@jwt_required
def api_get_import_settings():
    """Get user's import settings.

    Returns:
        {"settings": {...}}
    """
    settings = ImportSettings.get_or_create(g.current_user_id)

    return jsonify({
        'settings': settings.to_dict()
    })


@api_v1_bp.route('/import/settings', methods=['PUT'])
@jwt_required
def api_update_import_settings():
    """Update user's import settings.

    Request body (all fields optional):
        {
            "default_currency": "USD",
            "default_split_category": "SHARED",
            "auto_skip_duplicates": true,
            "auto_select_high_confidence": true,
            "confidence_threshold": 0.7
        }

    Returns:
        {"settings": {...}}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    settings = ImportSettings.get_or_create(g.current_user_id)

    # Update fields
    if 'default_currency' in data:
        if data['default_currency'] not in ['USD', 'CAD']:
            return jsonify({'error': 'Invalid currency'}), 400
        settings.default_currency = data['default_currency']

    if 'default_split_category' in data:
        settings.default_split_category = data['default_split_category']

    if 'auto_skip_duplicates' in data:
        settings.auto_skip_duplicates = bool(data['auto_skip_duplicates'])

    if 'auto_select_high_confidence' in data:
        settings.auto_select_high_confidence = bool(data['auto_select_high_confidence'])

    if 'confidence_threshold' in data:
        threshold = float(data['confidence_threshold'])
        if not 0.0 <= threshold <= 1.0:
            return jsonify({'error': 'Confidence threshold must be between 0 and 1'}), 400
        settings.confidence_threshold = threshold

    db.session.commit()

    return jsonify({
        'settings': settings.to_dict()
    })
