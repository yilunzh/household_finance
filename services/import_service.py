"""
Bank Import Service - handles file storage, extraction, and import logic.
"""
import os
import uuid
import json
from datetime import datetime, timedelta
from decimal import Decimal
from abc import ABC, abstractmethod

from flask import current_app
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    ImportSession, ExtractedTransaction, ImportSettings, ImportAuditLog,
    Transaction, AutoCategoryRule, ExpenseType
)


# =============================================================================
# File Storage
# =============================================================================

# Allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'heic'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_SESSION_SIZE = 50 * 1024 * 1024  # 50MB per session
MAX_FILES_PER_SESSION = 5


def get_import_folder():
    """Get the import folder path, creating it if needed."""
    # Use /data/imports in production, instance/imports in dev
    if os.environ.get('FLASK_ENV') == 'production':
        folder = '/data/imports'
    else:
        folder = os.path.join(
            current_app.instance_path if current_app else 'instance',
            'imports'
        )
    os.makedirs(folder, exist_ok=True)
    return folder


def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_type(filename):
    """Get file type (pdf or image) from filename."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext == 'pdf':
        return 'pdf'
    return 'image'


def generate_secure_filename(original_filename, session_id):
    """Generate a secure unique filename."""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    return f"import_{session_id}_{timestamp}_{unique_id}.{ext}"


def secure_delete(file_path):
    """Securely delete a file by overwriting with random data before removal."""
    if not os.path.exists(file_path):
        return

    try:
        # Get file size
        file_size = os.path.getsize(file_path)

        # Overwrite with random data
        with open(file_path, 'wb') as f:
            f.write(os.urandom(file_size))

        # Remove the file
        os.remove(file_path)
    except (IOError, OSError) as e:
        # If secure delete fails, try regular delete
        try:
            os.remove(file_path)
        except (IOError, OSError):
            current_app.logger.error(f"Failed to delete file {file_path}: {e}")


def delete_session_files(session):
    """Delete all files associated with an import session."""
    if not session.source_files:
        return

    files = json.loads(session.source_files)
    for file_info in files:
        file_path = file_info.get('path')
        if file_path and os.path.exists(file_path):
            secure_delete(file_path)

    # Clear the source_files JSON
    session.source_files = '[]'
    db.session.commit()


# =============================================================================
# Extraction Service Interface
# =============================================================================

class ExtractionService(ABC):
    """Abstract base class for document extraction services."""

    @abstractmethod
    def extract(self, file_path, file_type):
        """Extract transactions from a document.

        Args:
            file_path: Path to the file
            file_type: 'pdf' or 'image'

        Returns:
            List of dicts with keys: merchant, amount, currency, date, raw_text, confidence
        """
        pass


class MockExtractionService(ExtractionService):
    """Mock extraction service for testing."""

    def extract(self, file_path, file_type):
        """Return mock transactions for testing."""
        # Generate some realistic mock data
        return [
            {
                'merchant': 'Whole Foods Market',
                'amount': 85.43,
                'currency': 'USD',
                'date': datetime.now().date() - timedelta(days=1),
                'raw_text': 'WHOLE FOODS MARKET #10234 85.43',
                'confidence': 0.95
            },
            {
                'merchant': 'Amazon.com',
                'amount': 29.99,
                'currency': 'USD',
                'date': datetime.now().date() - timedelta(days=2),
                'raw_text': 'AMAZON.COM*123ABC 29.99',
                'confidence': 0.92
            },
            {
                'merchant': 'Shell Gas Station',
                'amount': 45.00,
                'currency': 'USD',
                'date': datetime.now().date() - timedelta(days=3),
                'raw_text': 'SHELL OIL 57432 45.00',
                'confidence': 0.88
            },
            {
                'merchant': 'Target',
                'amount': 127.84,
                'currency': 'USD',
                'date': datetime.now().date() - timedelta(days=4),
                'raw_text': 'TARGET T-1234 127.84',
                'confidence': 0.91
            },
            {
                'merchant': 'Starbucks',
                'amount': 6.75,
                'currency': 'USD',
                'date': datetime.now().date() - timedelta(days=5),
                'raw_text': 'STARBUCKS STORE 12345 6.75',
                'confidence': 0.94
            },
            {
                'merchant': 'Unknown Merchant',
                'amount': 15.00,
                'currency': 'USD',
                'date': datetime.now().date() - timedelta(days=6),
                'raw_text': 'XYZ123 PAYMENT 15.00',
                'confidence': 0.45  # Low confidence - needs review
            }
        ]


class GPT4VExtractionService(ExtractionService):
    """GPT-4V based extraction service."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')

    def extract(self, file_path, file_type):
        """Extract transactions using GPT-4V.

        For now, falls back to mock service if API not configured.
        """
        if not self.api_key:
            current_app.logger.warning("OpenAI API key not configured, using mock extraction")
            return MockExtractionService().extract(file_path, file_type)

        # TODO: Implement actual GPT-4V extraction
        # For now, use mock
        return MockExtractionService().extract(file_path, file_type)


def get_extraction_service():
    """Get the configured extraction service."""
    service_type = os.environ.get('EXTRACTION_SERVICE', 'mock')

    if service_type == 'gpt4v':
        return GPT4VExtractionService()
    else:
        return MockExtractionService()


# =============================================================================
# Rule Matching
# =============================================================================

def match_rules(merchant, household_id):
    """Match merchant against auto-categorization rules.

    Args:
        merchant: Merchant name to match
        household_id: Household ID to get rules for

    Returns:
        Dict with expense_type_id and split_category if match found, else None
    """
    # Get all rules for household, ordered by keyword length (longest first for specificity)
    rules = AutoCategoryRule.query.filter_by(
        household_id=household_id
    ).order_by(db.func.length(AutoCategoryRule.keyword).desc()).all()

    merchant_lower = merchant.lower()

    for rule in rules:
        if rule.keyword.lower() in merchant_lower:
            return {
                'expense_type_id': rule.expense_type_id,
                'split_category': 'SHARED'  # Default, could extend rule model
            }

    return None


def detect_duplicate(merchant, amount, date, household_id, tolerance_days=1):
    """Detect if a transaction might be a duplicate.

    Args:
        merchant: Merchant name
        amount: Transaction amount
        date: Transaction date
        household_id: Household ID
        tolerance_days: Date tolerance for matching

    Returns:
        Transaction ID if duplicate found, else None
    """
    from sqlalchemy import func, and_

    # Check for existing transactions with same merchant, amount, and similar date
    date_from = date - timedelta(days=tolerance_days)
    date_to = date + timedelta(days=tolerance_days)

    # Normalize merchant for comparison
    merchant_pattern = f"%{merchant.lower()[:20]}%"  # First 20 chars

    duplicate = Transaction.query.filter(
        and_(
            Transaction.household_id == household_id,
            func.lower(Transaction.merchant).like(merchant_pattern),
            Transaction.amount == amount,
            Transaction.date.between(date_from, date_to)
        )
    ).first()

    return duplicate.id if duplicate else None


# =============================================================================
# Import Service
# =============================================================================

class ImportService:
    """Main service for handling bank imports."""

    class ValidationError(Exception):
        """Raised when validation fails."""
        pass

    @staticmethod
    def create_session(user_id, household_id, files):
        """Create a new import session with uploaded files.

        Args:
            user_id: User ID
            household_id: Household ID
            files: List of FileStorage objects

        Returns:
            ImportSession instance

        Raises:
            ValidationError: If files are invalid
        """
        if not files:
            raise ImportService.ValidationError("No files provided")

        if len(files) > MAX_FILES_PER_SESSION:
            raise ImportService.ValidationError(
                f"Maximum {MAX_FILES_PER_SESSION} files per import"
            )

        # Create session first to get ID
        session = ImportSession(
            user_id=user_id,
            household_id=household_id,
            status=ImportSession.STATUS_PENDING
        )
        db.session.add(session)
        db.session.flush()  # Get ID without committing

        # Process and save files
        saved_files = []
        total_size = 0

        for file in files:
            if not file or not file.filename:
                continue

            if not allowed_file(file.filename):
                raise ImportService.ValidationError(
                    f"File type not allowed: {file.filename}. "
                    f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
                )

            # Check file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)

            if file_size > MAX_FILE_SIZE:
                raise ImportService.ValidationError(
                    f"File too large: {file.filename}. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
                )

            total_size += file_size
            if total_size > MAX_SESSION_SIZE:
                raise ImportService.ValidationError(
                    f"Total file size exceeds {MAX_SESSION_SIZE // (1024*1024)}MB limit"
                )

            # Generate secure filename and save
            original_name = secure_filename(file.filename)
            new_filename = generate_secure_filename(original_name, session.id)
            file_path = os.path.join(get_import_folder(), new_filename)

            file.save(file_path)

            saved_files.append({
                'path': file_path,
                'original_name': original_name,
                'type': get_file_type(original_name),
                'size': file_size
            })

        if not saved_files:
            raise ImportService.ValidationError("No valid files provided")

        session.source_files = json.dumps(saved_files)
        db.session.commit()

        # Log the upload
        ImportAuditLog.log(
            user_id=user_id,
            action=ImportAuditLog.ACTION_UPLOAD,
            session_id=session.id,
            details={'file_count': len(saved_files), 'total_size': total_size}
        )

        return session

    @staticmethod
    def process_session(session_id):
        """Process an import session (extract transactions).

        This should be called in a background thread.

        Args:
            session_id: Import session ID
        """
        session = ImportSession.query.get(session_id)
        if not session:
            return

        if session.status != ImportSession.STATUS_PENDING:
            return

        # Update status to processing
        session.status = ImportSession.STATUS_PROCESSING
        session.processing_started_at = datetime.utcnow()
        db.session.commit()

        ImportAuditLog.log(
            user_id=session.user_id,
            action=ImportAuditLog.ACTION_PROCESS_START,
            session_id=session.id
        )

        try:
            # Get extraction service
            extractor = get_extraction_service()

            # Get user settings
            settings = ImportSettings.get_or_create(session.user_id)

            # Process each file
            files = json.loads(session.source_files)
            all_transactions = []

            for file_info in files:
                file_path = file_info['path']
                file_type = file_info['type']

                if not os.path.exists(file_path):
                    continue

                # Extract transactions
                extracted = extractor.extract(file_path, file_type)
                all_transactions.extend(extracted)

            # Create ExtractedTransaction records
            for txn_data in all_transactions:
                # Match against rules
                rule_match = match_rules(txn_data['merchant'], session.household_id)

                # Check for duplicates
                duplicate_id = detect_duplicate(
                    txn_data['merchant'],
                    Decimal(str(txn_data['amount'])),
                    txn_data['date'],
                    session.household_id
                )

                # Build flags
                flags = {}
                if txn_data['confidence'] < settings.confidence_threshold:
                    flags['low_confidence'] = True
                if duplicate_id:
                    flags['duplicate_of'] = duplicate_id
                    if settings.auto_skip_duplicates:
                        flags['auto_skipped'] = True

                # Create extracted transaction
                ext_txn = ExtractedTransaction(
                    session_id=session.id,
                    merchant=txn_data['merchant'],
                    amount=Decimal(str(txn_data['amount'])),
                    currency=txn_data.get('currency', settings.default_currency),
                    date=txn_data['date'],
                    raw_text=txn_data.get('raw_text'),
                    confidence=txn_data['confidence'],
                    expense_type_id=rule_match['expense_type_id'] if rule_match else None,
                    split_category=rule_match['split_category'] if rule_match else settings.default_split_category,
                    is_selected=not flags.get('auto_skipped', False),
                    status=ExtractedTransaction.STATUS_PENDING,
                    flags=json.dumps(flags)
                )
                db.session.add(ext_txn)

            # Update session status
            session.status = ImportSession.STATUS_READY
            session.processing_completed_at = datetime.utcnow()
            db.session.commit()

            ImportAuditLog.log(
                user_id=session.user_id,
                action=ImportAuditLog.ACTION_PROCESS_COMPLETE,
                session_id=session.id,
                details={'transaction_count': len(all_transactions)}
            )

        except Exception as e:
            session.status = ImportSession.STATUS_FAILED
            session.error_message = str(e)
            session.processing_completed_at = datetime.utcnow()
            db.session.commit()

            ImportAuditLog.log(
                user_id=session.user_id,
                action=ImportAuditLog.ACTION_PROCESS_FAIL,
                session_id=session.id,
                details={'error': str(e)}
            )

    @staticmethod
    def get_session(session_id, user_id):
        """Get an import session, verifying ownership.

        Args:
            session_id: Session ID
            user_id: User ID (for ownership check)

        Returns:
            ImportSession or None
        """
        return ImportSession.query.filter_by(
            id=session_id,
            user_id=user_id
        ).first()

    @staticmethod
    def get_session_transactions(session_id, user_id, filters=None):
        """Get transactions for a session with optional filters.

        Args:
            session_id: Session ID
            user_id: User ID (for ownership check)
            filters: Dict with optional keys: status, is_selected, needs_review

        Returns:
            List of ExtractedTransaction or None if session not found
        """
        session = ImportService.get_session(session_id, user_id)
        if not session:
            return None

        query = ExtractedTransaction.query.filter_by(session_id=session_id)

        if filters:
            if 'status' in filters and filters['status']:
                query = query.filter_by(status=filters['status'])
            if 'is_selected' in filters and filters['is_selected'] is not None:
                query = query.filter_by(is_selected=filters['is_selected'])

        # Order by date descending
        query = query.order_by(ExtractedTransaction.date.desc())

        return query.all()

    @staticmethod
    def update_transaction(session_id, transaction_id, user_id, data):
        """Update an extracted transaction.

        Args:
            session_id: Session ID
            transaction_id: Transaction ID
            user_id: User ID (for ownership check)
            data: Dict with fields to update

        Returns:
            Updated ExtractedTransaction

        Raises:
            ValidationError: If validation fails
        """
        session = ImportService.get_session(session_id, user_id)
        if not session:
            raise ImportService.ValidationError("Session not found")

        txn = ExtractedTransaction.query.filter_by(
            id=transaction_id,
            session_id=session_id
        ).first()

        if not txn:
            raise ImportService.ValidationError("Transaction not found")

        # Update allowed fields
        if 'merchant' in data:
            txn.merchant = data['merchant']
        if 'amount' in data:
            txn.amount = Decimal(str(data['amount']))
        if 'date' in data:
            if isinstance(data['date'], str):
                txn.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            else:
                txn.date = data['date']
        if 'expense_type_id' in data:
            # Validate expense type belongs to household
            if data['expense_type_id']:
                exp_type = ExpenseType.query.filter_by(
                    id=data['expense_type_id'],
                    household_id=session.household_id
                ).first()
                if not exp_type:
                    raise ImportService.ValidationError("Invalid expense type")
            txn.expense_type_id = data['expense_type_id']
        if 'split_category' in data:
            txn.split_category = data['split_category']
        if 'is_selected' in data:
            txn.is_selected = data['is_selected']

        # Mark as reviewed after manual edit
        if txn.status == ExtractedTransaction.STATUS_PENDING:
            txn.status = ExtractedTransaction.STATUS_REVIEWED

        # Clear OCR uncertainty flag after manual edit
        flags = json.loads(txn.flags) if txn.flags else {}
        if 'ocr_uncertain' in flags:
            del flags['ocr_uncertain']
            txn.flags = json.dumps(flags)

        db.session.commit()
        return txn

    @staticmethod
    def import_transactions(session_id, user_id, transaction_ids=None):
        """Import selected transactions into the main transaction table.

        Args:
            session_id: Session ID
            user_id: User ID
            transaction_ids: Optional list of specific transaction IDs to import.
                           If None, imports all selected transactions.

        Returns:
            Number of transactions imported

        Raises:
            ValidationError: If import fails
        """
        session = ImportService.get_session(session_id, user_id)
        if not session:
            raise ImportService.ValidationError("Session not found")

        if session.status not in [ImportSession.STATUS_READY, ImportSession.STATUS_PROCESSING]:
            raise ImportService.ValidationError(
                f"Cannot import from session with status: {session.status}"
            )

        # Get transactions to import
        query = ExtractedTransaction.query.filter_by(
            session_id=session_id,
            is_selected=True
        ).filter(
            ExtractedTransaction.status.in_([
                ExtractedTransaction.STATUS_PENDING,
                ExtractedTransaction.STATUS_REVIEWED
            ])
        )

        if transaction_ids:
            query = query.filter(ExtractedTransaction.id.in_(transaction_ids))

        transactions_to_import = query.all()

        if not transactions_to_import:
            raise ImportService.ValidationError("No transactions to import")

        imported_count = 0

        for ext_txn in transactions_to_import:
            # Create real transaction
            month_year = ext_txn.date.strftime('%Y-%m')

            # Convert to USD if needed (simplified - assumes 1:1 for now)
            amount_in_usd = ext_txn.amount

            txn = Transaction(
                household_id=session.household_id,
                date=ext_txn.date,
                merchant=ext_txn.merchant,
                amount=ext_txn.amount,
                currency=ext_txn.currency,
                amount_in_usd=amount_in_usd,
                paid_by_user_id=user_id,
                category=ext_txn.split_category,
                expense_type_id=ext_txn.expense_type_id,
                notes=f"Imported from bank statement",
                month_year=month_year
            )
            db.session.add(txn)

            # Update extracted transaction status
            ext_txn.status = ExtractedTransaction.STATUS_IMPORTED
            imported_count += 1

        # Mark non-selected as skipped
        ExtractedTransaction.query.filter_by(
            session_id=session_id,
            is_selected=False
        ).filter(
            ExtractedTransaction.status == ExtractedTransaction.STATUS_PENDING
        ).update({'status': ExtractedTransaction.STATUS_SKIPPED})

        # Update session
        session.status = ImportSession.STATUS_COMPLETED
        session.imported_at = datetime.utcnow()
        db.session.commit()

        # Delete source files immediately after import
        delete_session_files(session)

        ImportAuditLog.log(
            user_id=user_id,
            action=ImportAuditLog.ACTION_IMPORT,
            session_id=session_id,
            details={'imported_count': imported_count}
        )

        ImportAuditLog.log(
            user_id=user_id,
            action=ImportAuditLog.ACTION_DELETE_FILES,
            session_id=session_id
        )

        return imported_count

    @staticmethod
    def delete_session(session_id, user_id):
        """Delete an import session and its files.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            True if deleted

        Raises:
            ValidationError: If session not found
        """
        session = ImportService.get_session(session_id, user_id)
        if not session:
            raise ImportService.ValidationError("Session not found")

        # Delete files first
        delete_session_files(session)

        ImportAuditLog.log(
            user_id=user_id,
            action=ImportAuditLog.ACTION_DELETE_SESSION,
            session_id=session_id
        )

        # Delete session (cascades to extracted transactions)
        db.session.delete(session)
        db.session.commit()

        return True

    @staticmethod
    def cleanup_expired_sessions(days=7):
        """Clean up old incomplete sessions.

        Args:
            days: Number of days after which to clean up

        Returns:
            Number of sessions cleaned up
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        expired_sessions = ImportSession.query.filter(
            ImportSession.status.in_([
                ImportSession.STATUS_PENDING,
                ImportSession.STATUS_PROCESSING,
                ImportSession.STATUS_READY,
                ImportSession.STATUS_FAILED
            ]),
            ImportSession.created_at < cutoff
        ).all()

        count = 0
        for session in expired_sessions:
            delete_session_files(session)
            db.session.delete(session)
            count += 1

        db.session.commit()
        return count
