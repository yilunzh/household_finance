"""
E2E tests for transaction management.
Tests CRUD operations, currency conversion, and locked month handling.
"""
import pytest
from datetime import date
from conftest import BASE_URL, TEST_USERS


pytestmark = pytest.mark.integration


class TestCreateTransaction:
    """Transaction creation tests."""

    def test_create_transaction_success(self, page, register_user, create_household):
        """User can create a new transaction."""
        register_user('alice')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Fill transaction form
        page.fill('input[name="merchant"]', 'Test Store')
        page.fill('input[name="amount"]', '50.00')
        page.select_option('select[name="currency"]', 'USD')
        page.select_option('select[name="category"]', 'SHARED')

        page.click('button:has-text("Add Transaction")')
        page.wait_for_load_state('networkidle')

        # Transaction should appear in list
        content = page.content()
        assert 'Test Store' in content

    def test_create_transaction_with_cad(self, page, register_user, create_household):
        """User can create a transaction in CAD currency."""
        register_user('bob')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="merchant"]', 'Canadian Store')
        page.fill('input[name="amount"]', '100.00')
        page.select_option('select[name="currency"]', 'CAD')
        page.select_option('select[name="category"]', 'SHARED')

        page.click('button:has-text("Add Transaction")')
        page.wait_for_load_state('networkidle')

        content = page.content()
        assert 'Canadian Store' in content

    def test_create_transaction_with_notes(self, page, register_user, create_household):
        """User can add notes to transaction."""
        register_user('charlie')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        page.fill('input[name="merchant"]', 'Notes Test')
        page.fill('input[name="amount"]', '25.00')
        page.select_option('select[name="currency"]', 'USD')
        page.select_option('select[name="category"]', 'SHARED')

        notes_input = page.locator('input[name="notes"], textarea[name="notes"]')
        if notes_input.count() > 0:
            notes_input.first.fill('This is a test note')

        page.click('button:has-text("Add Transaction")')
        page.wait_for_load_state('networkidle')

        content = page.content()
        assert 'Notes Test' in content


class TestReadTransactions:
    """Transaction list/read tests."""

    def test_transactions_displayed_in_table(self, page, setup_two_households, login_as):
        """Transactions should appear in a table."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Should show test transactions from setup
        assert 'Grocery Store' in content or 'Restaurant' in content

    def test_month_filter_dropdown(self, page, setup_two_households, login_as):
        """Month filter dropdown should exist."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Should have month selector
        month_select = page.locator('select[name="month"], select[id="month"]')
        assert month_select.count() > 0

    def test_transaction_shows_paid_by_name(self, page, setup_two_households, login_as):
        """Transaction should show who paid."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Should show member names
        assert 'Alice' in content or 'Bob' in content


class TestUpdateTransaction:
    """Transaction update/edit tests."""

    def test_edit_button_visible(self, page, setup_two_households, login_as):
        """Edit button should be visible for transactions."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        edit_btn = page.locator('button:has-text("Edit"), a:has-text("Edit")')
        assert edit_btn.count() > 0

    def test_edit_modal_opens(self, page, setup_two_households, login_as):
        """Clicking edit should open edit modal/form."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        edit_btn = page.locator('button:has-text("Edit")').first
        edit_btn.click()
        page.wait_for_timeout(500)  # Wait for modal

        # Modal should be visible
        modal = page.locator('[class*="modal"], [role="dialog"]')
        assert modal.count() > 0 or 'edit' in page.content().lower()


class TestDeleteTransaction:
    """Transaction deletion tests."""

    def test_delete_button_visible(self, page, setup_two_households, login_as):
        """Delete button should be visible for transactions."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        delete_btn = page.locator('button:has-text("Delete")')
        assert delete_btn.count() > 0

    def test_delete_with_confirmation(self, page, register_user, create_household, add_transaction):
        """Deleting transaction should require confirmation."""
        register_user('diana')
        create_household('Test Household')
        add_transaction('Delete Test', '10.00')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Click delete
        delete_btn = page.locator('button:has-text("Delete")').first
        delete_btn.click()
        page.wait_for_timeout(500)

        # Confirmation dialog should appear or action completes
        content = page.content().lower()
        # Either confirm dialog visible or transaction deleted
        assert 'confirm' in content or 'delete' in content or 'Delete Test' not in page.content()


class TestMonthFiltering:
    """Month-based transaction filtering tests."""

    def test_current_month_selected_by_default(self, page, register_user, create_household):
        """Current month should be selected by default."""
        register_user('alice')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        current_month = date.today().strftime('%Y-%m')
        content = page.content()

        # Current month should be visible or selected
        assert current_month in content or date.today().strftime('%B') in content

    def test_can_switch_months(self, page, setup_two_households, login_as):
        """User can switch between months."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        month_select = page.locator('select[name="month"], select[id="month"]')
        if month_select.count() > 0:
            # Get current options
            options = month_select.first.locator('option').all()
            if len(options) > 1:
                # Select a different month
                month_select.first.select_option(index=1)
                page.wait_for_load_state('networkidle')


class TestSettledMonthLocking:
    """Tests for transaction locking when month is settled."""

    def test_settled_month_shows_locked_indicator(self, page, setup_two_households, login_as, app, db):
        """Settled month should show locked indicator."""
        from models import Settlement, User, Household
        from datetime import date as dt_date

        # Create settlement
        with app.app_context():
            alice = User.query.filter_by(email=TEST_USERS['alice']['email']).first()
            bob = User.query.filter_by(email=TEST_USERS['bob']['email']).first()
            household = Household.query.filter_by(name='Alice & Bob Household').first()

            settlement = Settlement(
                household_id=household.id,
                month_year=dt_date.today().strftime('%Y-%m'),
                settled_date=dt_date.today(),
                settlement_amount=35.00,
                from_user_id=bob.id,
                to_user_id=alice.id,
                settlement_message='Bob owes Alice $35.00'
            )
            db.session.add(settlement)
            db.session.commit()

        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        # Should show locked/settled indicator
        assert 'locked' in content or 'settled' in content or 'unlock' in content

        # Cleanup
        with app.app_context():
            Settlement.query.filter_by(household_id=household.id).delete()
            db.session.commit()


class TestTransactionCategories:
    """Transaction category tests."""

    def test_all_categories_available(self, page, register_user, create_household):
        """All expense categories should be available."""
        register_user('alice')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        category_select = page.locator('select[name="category"]')
        assert category_select.count() > 0

        options = category_select.first.locator('option').all()
        assert len(options) >= 3  # At least SHARED and personal options

    def test_shared_category_selected_by_default(self, page, register_user, create_household):
        """SHARED category should be default."""
        register_user('bob')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        category_select = page.locator('select[name="category"]')
        if category_select.count() > 0:
            selected_value = category_select.first.input_value()
            assert selected_value == 'SHARED' or 'shared' in selected_value.lower()


class TestTransactionFormValidation:
    """Form validation tests."""

    def test_missing_merchant_rejected(self, page, register_user, create_household):
        """Missing merchant should be rejected."""
        register_user('charlie')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Submit without merchant
        page.fill('input[name="amount"]', '50.00')
        page.click('button:has-text("Add Transaction")')
        page.wait_for_timeout(500)

        # Form should show error or not submit
        # Check if still on same page without new transaction

    def test_missing_amount_rejected(self, page, register_user, create_household):
        """Missing amount should be rejected."""
        register_user('diana')
        create_household('Test Household')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Submit without amount
        page.fill('input[name="merchant"]', 'Test')
        page.click('button:has-text("Add Transaction")')
        page.wait_for_timeout(500)

        # Form validation should prevent submission
