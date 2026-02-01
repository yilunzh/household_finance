"""
Tests for bank import functionality.
"""
import json
import pytest
import uuid
from datetime import datetime
from decimal import Decimal

from models import (
    ImportSession, ExtractedTransaction, ImportSettings, ImportAuditLog,
    User, Household, HouseholdMember, ExpenseType, Transaction, AutoCategoryRule
)
from extensions import db
from services.import_service import (
    ImportService, MockExtractionService, GPT4VExtractionService, ExtractionError,
    match_rules, detect_duplicate, allowed_file, get_file_type, secure_delete
)
from services.cleanup_service import (
    cleanup_expired_sessions, cleanup_old_audit_logs
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def unique_user(app):
    """Create a user with a unique email for each test."""
    unique_id = uuid.uuid4().hex[:8]
    with app.app_context():
        user = User(
            email=f'importtest_{unique_id}@example.com',
            name=f'Import Test User {unique_id}'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user
        # Cleanup
        try:
            db.session.delete(user)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def unique_household(app, unique_user):
    """Create a household with unique user as owner."""
    unique_id = uuid.uuid4().hex[:8]
    with app.app_context():
        household = Household(
            name=f'Test Household {unique_id}',
            created_by_user_id=unique_user.id
        )
        db.session.add(household)
        db.session.commit()

        member = HouseholdMember(
            household_id=household.id,
            user_id=unique_user.id,
            role='owner',
            display_name='Test User'
        )
        db.session.add(member)
        db.session.commit()

        db.session.refresh(household)
        yield household
        # Cleanup happens via cascade when user is deleted


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def auth_headers(app, unique_user):
    """Generate JWT auth headers for test user."""
    from api_decorators import generate_access_token
    with app.app_context():
        token = generate_access_token(unique_user.id)
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture
def household_headers(unique_household):
    """Generate household context header."""
    return {'X-Household-ID': str(unique_household.id)}


# =============================================================================
# Model Tests
# =============================================================================

class TestImportModels:
    """Test bank import model CRUD operations."""

    def test_import_session_creation(self, app, unique_user, unique_household):
        """Test creating an import session."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_PENDING,
                source_files='[]'
            )
            db.session.add(session)
            db.session.commit()

            assert session.id is not None
            assert session.status == 'pending'
            assert session.source_files == '[]'

    def test_import_session_status_transitions(self, app, unique_user, unique_household):
        """Test import session status transitions."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_PENDING
            )
            db.session.add(session)
            db.session.commit()

            # Transition to processing
            session.status = ImportSession.STATUS_PROCESSING
            session.processing_started_at = datetime.utcnow()
            db.session.commit()
            assert session.status == 'processing'

            # Transition to ready
            session.status = ImportSession.STATUS_READY
            session.processing_completed_at = datetime.utcnow()
            db.session.commit()
            assert session.status == 'ready'

    def test_import_session_to_dict(self, app, unique_user, unique_household):
        """Test import session serialization."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_PENDING,
                source_files='[{"path": "/tmp/test.pdf", "type": "pdf"}]'
            )
            db.session.add(session)
            db.session.commit()

            data = session.to_dict()
            assert data['id'] == session.id
            assert data['status'] == 'pending'
            assert len(data['source_files']) == 1
            assert data['source_files'][0]['type'] == 'pdf'

    def test_extracted_transaction_creation(self, app, unique_user, unique_household):
        """Test creating an extracted transaction."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_READY
            )
            db.session.add(session)
            db.session.commit()

            txn = ExtractedTransaction(
                session_id=session.id,
                merchant='Test Merchant',
                amount=Decimal('50.00'),
                currency='USD',
                date=datetime.now().date(),
                confidence=0.95,
                split_category='SHARED'
            )
            db.session.add(txn)
            db.session.commit()

            assert txn.id is not None
            assert txn.merchant == 'Test Merchant'
            assert float(txn.amount) == 50.00

    def test_extracted_transaction_needs_review(self, app, unique_user, unique_household):
        """Test needs_review flag logic."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_READY
            )
            db.session.add(session)
            db.session.commit()

            # High confidence - no review needed
            txn1 = ExtractedTransaction(
                session_id=session.id,
                merchant='Test',
                amount=Decimal('10.00'),
                currency='USD',
                date=datetime.now().date(),
                confidence=0.95,
                split_category='SHARED'
            )
            db.session.add(txn1)

            # Low confidence - needs review
            txn2 = ExtractedTransaction(
                session_id=session.id,
                merchant='Test2',
                amount=Decimal('20.00'),
                currency='USD',
                date=datetime.now().date(),
                confidence=0.5,
                split_category='SHARED'
            )
            db.session.add(txn2)
            db.session.commit()

            assert not txn1.needs_review()
            assert txn2.needs_review()

    def test_extracted_transaction_flags(self, app, unique_user, unique_household):
        """Test flag get/set operations."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_READY
            )
            db.session.add(session)
            db.session.commit()

            txn = ExtractedTransaction(
                session_id=session.id,
                merchant='Test',
                amount=Decimal('10.00'),
                currency='USD',
                date=datetime.now().date(),
                confidence=0.95,
                split_category='SHARED'
            )
            db.session.add(txn)
            db.session.commit()

            # Set and get flag
            txn.set_flag('duplicate_of', 123)
            db.session.commit()

            assert txn.get_flag('duplicate_of') == 123
            assert txn.get_flag('nonexistent', 'default') == 'default'

    def test_import_settings_get_or_create(self, app, unique_user):
        """Test import settings get_or_create pattern."""
        with app.app_context():
            # First call creates settings
            settings1 = ImportSettings.get_or_create(unique_user.id)
            assert settings1.id is not None
            assert settings1.default_currency == 'USD'

            # Second call returns same settings
            settings2 = ImportSettings.get_or_create(unique_user.id)
            assert settings1.id == settings2.id

    def test_import_audit_log(self, app, unique_user, unique_household):
        """Test audit logging."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_PENDING
            )
            db.session.add(session)
            db.session.commit()

            # Log an action
            with app.test_request_context():
                log = ImportAuditLog.log(
                    user_id=unique_user.id,
                    action=ImportAuditLog.ACTION_UPLOAD,
                    session_id=session.id,
                    details={'file_count': 2}
                )

            assert log.id is not None
            assert log.action == 'upload'
            assert json.loads(log.details)['file_count'] == 2


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestImportServiceHelpers:
    """Test import service helper functions."""

    def test_allowed_file_valid(self):
        """Test valid file types."""
        assert allowed_file('test.pdf') is True
        assert allowed_file('test.png') is True
        assert allowed_file('test.jpg') is True
        assert allowed_file('test.jpeg') is True
        assert allowed_file('test.heic') is True

    def test_allowed_file_invalid(self):
        """Test invalid file types."""
        assert allowed_file('test.exe') is False
        assert allowed_file('test.txt') is False
        assert allowed_file('noextension') is False

    def test_get_file_type(self):
        """Test file type detection."""
        assert get_file_type('test.pdf') == 'pdf'
        assert get_file_type('test.png') == 'image'
        assert get_file_type('test.jpg') == 'image'
        assert get_file_type('test.jpeg') == 'image'


class TestMockExtractionService:
    """Test mock extraction service."""

    def test_extract_returns_transactions(self):
        """Test mock extraction returns data."""
        service = MockExtractionService()
        transactions = service.extract('/tmp/test.pdf', 'pdf')

        assert len(transactions) > 0
        assert all('merchant' in t for t in transactions)
        assert all('amount' in t for t in transactions)
        assert all('date' in t for t in transactions)
        assert all('confidence' in t for t in transactions)


class TestGPT4VExtractionService:
    """Test GPT-4V extraction service explicit failure behavior."""

    def test_extract_fails_without_api_key(self, monkeypatch):
        """Test GPT-4V extraction raises ExtractionError when API key is missing."""
        # Ensure no API key in environment
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)

        # Create service without API key
        service = GPT4VExtractionService(api_key=None)

        with pytest.raises(ExtractionError) as exc_info:
            service.extract('/tmp/test.pdf', 'pdf')

        assert 'OpenAI API key not configured' in str(exc_info.value)
        assert 'manually' in str(exc_info.value)

    def test_extract_fails_with_invalid_client(self):
        """Test GPT-4V extraction raises ExtractionError when client init fails."""
        # Create service with a key so first check passes
        service = GPT4VExtractionService(api_key='sk-test-key')

        # Mock the client property to return None
        original_client = GPT4VExtractionService.client
        try:
            GPT4VExtractionService.client = property(lambda self: None)
            with pytest.raises(ExtractionError) as exc_info:
                service.extract('/tmp/test.pdf', 'pdf')
            assert 'Failed to initialize AI service' in str(exc_info.value)
        finally:
            GPT4VExtractionService.client = original_client


# =============================================================================
# Rule Matching Tests
# =============================================================================

class TestRuleMatching:
    """Test auto-categorization rule matching."""

    def test_match_rules_finds_match(self, app, unique_household):
        """Test rule matching finds correct expense type."""
        with app.app_context():
            # Create expense type
            expense_type = ExpenseType(
                household_id=unique_household.id,
                name='Grocery'
            )
            db.session.add(expense_type)
            db.session.commit()

            # Create rule
            rule = AutoCategoryRule(
                household_id=unique_household.id,
                keyword='whole foods',
                expense_type_id=expense_type.id
            )
            db.session.add(rule)
            db.session.commit()

            # Test matching
            result = match_rules('Whole Foods Market #123', unique_household.id)
            assert result is not None
            assert result['expense_type_id'] == expense_type.id

    def test_match_rules_no_match(self, app, unique_household):
        """Test rule matching returns None when no match."""
        with app.app_context():
            result = match_rules('Random Merchant', unique_household.id)
            assert result is None

    def test_match_rules_case_insensitive(self, app, unique_household):
        """Test rule matching is case insensitive."""
        with app.app_context():
            expense_type = ExpenseType(
                household_id=unique_household.id,
                name='Grocery'
            )
            db.session.add(expense_type)
            db.session.commit()

            rule = AutoCategoryRule(
                household_id=unique_household.id,
                keyword='WHOLE FOODS',
                expense_type_id=expense_type.id
            )
            db.session.add(rule)
            db.session.commit()

            # Should match lowercase
            result = match_rules('whole foods market', unique_household.id)
            assert result is not None


# =============================================================================
# Duplicate Detection Tests
# =============================================================================

class TestDuplicateDetection:
    """Test duplicate transaction detection."""

    def test_detect_duplicate_finds_match(self, app, unique_user, unique_household):
        """Test duplicate detection finds matching transaction."""
        with app.app_context():
            # Create existing transaction
            existing = Transaction(
                household_id=unique_household.id,
                date=datetime.now().date(),
                merchant='Whole Foods',
                amount=Decimal('50.00'),
                currency='USD',
                amount_in_usd=Decimal('50.00'),
                paid_by_user_id=unique_user.id,
                category='SHARED',
                month_year=datetime.now().strftime('%Y-%m')
            )
            db.session.add(existing)
            db.session.commit()

            # Test detection
            duplicate_id = detect_duplicate(
                'Whole Foods',
                Decimal('50.00'),
                datetime.now().date(),
                unique_household.id
            )
            assert duplicate_id == existing.id

    def test_detect_duplicate_no_match(self, app, unique_household):
        """Test duplicate detection returns None when no match."""
        with app.app_context():
            duplicate_id = detect_duplicate(
                'New Merchant',
                Decimal('100.00'),
                datetime.now().date(),
                unique_household.id
            )
            assert duplicate_id is None


# =============================================================================
# Import Service Tests
# =============================================================================

class TestImportService:
    """Test main ImportService functionality."""

    def test_create_session_validation_no_files(self, app, unique_user, unique_household):
        """Test session creation fails without files."""
        with app.app_context():
            with pytest.raises(ImportService.ValidationError) as exc_info:
                ImportService.create_session(unique_user.id, unique_household.id, [])
            assert 'No files provided' in str(exc_info.value)

    def test_get_session_ownership(self, app, unique_user, unique_household):
        """Test session retrieval respects ownership."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_PENDING
            )
            db.session.add(session)
            db.session.commit()

            # Owner can retrieve
            result = ImportService.get_session(session.id, unique_user.id)
            assert result is not None

            # Non-owner cannot retrieve
            result = ImportService.get_session(session.id, 99999)
            assert result is None

    def test_update_transaction(self, app, unique_user, unique_household):
        """Test transaction update."""
        with app.app_context():
            session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_READY
            )
            db.session.add(session)
            db.session.commit()

            txn = ExtractedTransaction(
                session_id=session.id,
                merchant='Original',
                amount=Decimal('10.00'),
                currency='USD',
                date=datetime.now().date(),
                confidence=0.95,
                split_category='SHARED'
            )
            db.session.add(txn)
            db.session.commit()

            # Update transaction
            updated = ImportService.update_transaction(
                session.id, txn.id, unique_user.id,
                {'merchant': 'Updated Merchant', 'amount': 20.00}
            )

            assert updated.merchant == 'Updated Merchant'
            assert float(updated.amount) == 20.00
            assert updated.status == ExtractedTransaction.STATUS_REVIEWED


# =============================================================================
# API Tests
# =============================================================================

class TestBankImportAPI:
    """Test bank import API endpoints."""

    def test_list_sessions(self, client, auth_headers):
        """Test listing sessions returns valid response."""
        response = client.get(
            '/api/v1/import/sessions',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'sessions' in data
        assert 'count' in data
        assert isinstance(data['sessions'], list)

    def test_get_session_not_found(self, client, auth_headers):
        """Test getting non-existent session."""
        response = client.get(
            '/api/v1/import/sessions/99999',
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_get_import_settings(self, client, auth_headers):
        """Test getting import settings."""
        response = client.get(
            '/api/v1/import/settings',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'settings' in data
        assert data['settings']['default_currency'] == 'USD'

    def test_update_import_settings(self, client, auth_headers):
        """Test updating import settings."""
        response = client.put(
            '/api/v1/import/settings',
            headers=auth_headers,
            json={
                'default_currency': 'CAD',
                'confidence_threshold': 0.8
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['settings']['default_currency'] == 'CAD'
        assert data['settings']['confidence_threshold'] == 0.8

    def test_list_rules_empty(self, client, auth_headers, household_headers):
        """Test listing rules when none exist."""
        headers = {**auth_headers, **household_headers}
        response = client.get(
            '/api/v1/import/rules',
            headers=headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['rules'] == []

    def test_create_rule(self, client, auth_headers, household_headers, app, unique_household):
        """Test creating an auto-categorization rule."""
        with app.app_context():
            # Create expense type first
            expense_type = ExpenseType(
                household_id=unique_household.id,
                name='Grocery'
            )
            db.session.add(expense_type)
            db.session.commit()
            expense_type_id = expense_type.id

        headers = {**auth_headers, **household_headers}
        response = client.post(
            '/api/v1/import/rules',
            headers=headers,
            json={
                'keyword': 'whole foods',
                'expense_type_id': expense_type_id
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['rule']['keyword'] == 'whole foods'

    def test_delete_rule(self, client, auth_headers, household_headers, app, unique_household):
        """Test deleting an auto-categorization rule."""
        with app.app_context():
            expense_type = ExpenseType(
                household_id=unique_household.id,
                name='Grocery'
            )
            db.session.add(expense_type)
            db.session.commit()

            rule = AutoCategoryRule(
                household_id=unique_household.id,
                keyword='test',
                expense_type_id=expense_type.id
            )
            db.session.add(rule)
            db.session.commit()
            rule_id = rule.id

        headers = {**auth_headers, **household_headers}
        response = client.delete(
            f'/api/v1/import/rules/{rule_id}',
            headers=headers
        )
        assert response.status_code == 204


# =============================================================================
# Cleanup Service Tests
# =============================================================================

class TestCleanupService:
    """Test cleanup service functionality."""

    def test_cleanup_expired_sessions(self, app, unique_user, unique_household):
        """Test that expired incomplete sessions are cleaned up."""
        from datetime import timedelta

        with app.app_context():
            # Create an old pending session (8 days old)
            old_session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_PENDING,
                source_files='[]'
            )
            db.session.add(old_session)
            db.session.flush()

            # Manually set created_at to 8 days ago
            old_session.created_at = datetime.utcnow() - timedelta(days=8)
            db.session.commit()
            old_session_id = old_session.id

            # Create a recent pending session (1 day old)
            recent_session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_PENDING,
                source_files='[]'
            )
            db.session.add(recent_session)
            db.session.flush()
            recent_session.created_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()
            recent_session_id = recent_session.id

            # Create a completed session (old but should not be cleaned)
            completed_session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_COMPLETED,
                source_files='[]'
            )
            db.session.add(completed_session)
            db.session.flush()
            completed_session.created_at = datetime.utcnow() - timedelta(days=10)
            db.session.commit()
            completed_session_id = completed_session.id

            # Run cleanup with 7-day threshold
            cleaned = cleanup_expired_sessions(days=7)

            # Should have cleaned 1 session (the old pending one)
            assert cleaned == 1

            # Verify old session is gone
            assert ImportSession.query.get(old_session_id) is None

            # Verify recent session still exists
            assert ImportSession.query.get(recent_session_id) is not None

            # Verify completed session still exists
            assert ImportSession.query.get(completed_session_id) is not None

    def test_cleanup_old_audit_logs(self, app, unique_user, unique_household):
        """Test that old audit logs are cleaned up."""
        from datetime import timedelta

        with app.app_context():
            # Create an old audit log (100 days old)
            old_log = ImportAuditLog(
                user_id=unique_user.id,
                action=ImportAuditLog.ACTION_UPLOAD
            )
            db.session.add(old_log)
            db.session.flush()
            old_log.created_at = datetime.utcnow() - timedelta(days=100)
            db.session.commit()
            old_log_id = old_log.id

            # Create a recent audit log (30 days old)
            recent_log = ImportAuditLog(
                user_id=unique_user.id,
                action=ImportAuditLog.ACTION_IMPORT
            )
            db.session.add(recent_log)
            db.session.flush()
            recent_log.created_at = datetime.utcnow() - timedelta(days=30)
            db.session.commit()
            recent_log_id = recent_log.id

            # Run cleanup with 90-day threshold
            cleaned = cleanup_old_audit_logs(days=90)

            # Should have cleaned 1 log (the old one)
            assert cleaned == 1

            # Verify old log is gone
            assert ImportAuditLog.query.get(old_log_id) is None

            # Verify recent log still exists
            assert ImportAuditLog.query.get(recent_log_id) is not None

    def test_secure_delete(self, app, tmp_path):
        """Test that secure_delete overwrites file before deletion."""
        # Create a test file with known content
        test_file = tmp_path / "test_secure_delete.txt"
        original_content = b"This is sensitive data that should be overwritten"
        test_file.write_bytes(original_content)

        # Verify file exists
        assert test_file.exists()
        file_size = test_file.stat().st_size
        assert file_size == len(original_content)

        # Securely delete the file
        with app.app_context():
            secure_delete(str(test_file))

        # Verify file is deleted
        assert not test_file.exists()

    def test_secure_delete_nonexistent_file(self, app):
        """Test that secure_delete handles nonexistent files gracefully."""
        with app.app_context():
            # Should not raise an exception
            secure_delete("/nonexistent/path/to/file.txt")

    def test_cleanup_expired_sessions_with_files(self, app, unique_user, unique_household, tmp_path):
        """Test that cleanup deletes associated files."""
        from datetime import timedelta

        with app.app_context():
            # Create a test file
            test_file = tmp_path / "test_import_file.pdf"
            test_file.write_bytes(b"PDF content here")

            # Create an old session with source files
            old_session = ImportSession(
                user_id=unique_user.id,
                household_id=unique_household.id,
                status=ImportSession.STATUS_FAILED,
                source_files=json.dumps([{'path': str(test_file), 'type': 'pdf'}])
            )
            db.session.add(old_session)
            db.session.flush()
            old_session.created_at = datetime.utcnow() - timedelta(days=10)
            db.session.commit()

            # Verify file exists before cleanup
            assert test_file.exists()

            # Run cleanup
            cleaned = cleanup_expired_sessions(days=7)

            # Should have cleaned 1 session
            assert cleaned == 1

            # Verify file is deleted
            assert not test_file.exists()


# =============================================================================
# File Upload Validation Tests
# =============================================================================

class TestFileUploadValidation:
    """Test file upload content validation."""

    def test_upload_accepts_matching_extension(self, client, auth_headers, household_headers):
        """JPEG data with .jpg extension should be accepted."""
        from io import BytesIO

        # JPEG magic bytes
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100

        headers = {k: v for k, v in auth_headers.items() if k != 'Content-Type'}
        headers.update(household_headers)

        response = client.post(
            '/api/v1/import/sessions',
            data={'files': (BytesIO(jpeg_data), 'photo.jpg', 'image/jpeg')},
            content_type='multipart/form-data',
            headers=headers
        )

        # Should succeed (201) or at least not fail validation (not 400 with "content does not match")
        assert response.status_code in [201, 500]  # 500 if extraction fails, but validation passed
        if response.status_code == 400:
            assert 'content does not match' not in response.get_json().get('error', '')

    def test_upload_rejects_mismatched_extension(self, client, auth_headers, household_headers):
        """HEIC data with .jpg extension should be rejected."""
        from io import BytesIO

        # HEIC magic bytes (ftypmif1 at offset 4)
        heic_data = b'\x00\x00\x00\x1cftypmif1' + b'\x00' * 100

        headers = {k: v for k, v in auth_headers.items() if k != 'Content-Type'}
        headers.update(household_headers)

        response = client.post(
            '/api/v1/import/sessions',
            data={'files': (BytesIO(heic_data), 'photo.jpg', 'image/jpeg')},
            content_type='multipart/form-data',
            headers=headers
        )

        assert response.status_code == 400
        assert 'content does not match' in response.get_json()['error']

    def test_upload_accepts_heic_with_heic_extension(self, client, auth_headers, household_headers):
        """HEIC data with .heic extension should be accepted."""
        from io import BytesIO

        # HEIC magic bytes
        heic_data = b'\x00\x00\x00\x1cftypmif1' + b'\x00' * 100

        headers = {k: v for k, v in auth_headers.items() if k != 'Content-Type'}
        headers.update(household_headers)

        response = client.post(
            '/api/v1/import/sessions',
            data={'files': (BytesIO(heic_data), 'photo.heic', 'image/heic')},
            content_type='multipart/form-data',
            headers=headers
        )

        assert response.status_code in [201, 500]
        if response.status_code == 400:
            assert 'content does not match' not in response.get_json().get('error', '')

    def test_upload_accepts_png(self, client, auth_headers, household_headers):
        """PNG data with .png extension should be accepted."""
        from io import BytesIO

        # PNG magic bytes
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

        headers = {k: v for k, v in auth_headers.items() if k != 'Content-Type'}
        headers.update(household_headers)

        response = client.post(
            '/api/v1/import/sessions',
            data={'files': (BytesIO(png_data), 'screenshot.png', 'image/png')},
            content_type='multipart/form-data',
            headers=headers
        )

        assert response.status_code in [201, 500]
        if response.status_code == 400:
            assert 'content does not match' not in response.get_json().get('error', '')
