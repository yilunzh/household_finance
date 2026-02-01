"""
Tests for bank import functionality.
"""
import json
import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from models import (
    ImportSession, ExtractedTransaction, ImportSettings, ImportAuditLog,
    User, Household, HouseholdMember, ExpenseType, Transaction, AutoCategoryRule
)
from extensions import db
from services.import_service import (
    ImportService, MockExtractionService, match_rules, detect_duplicate,
    allowed_file, get_file_type
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
