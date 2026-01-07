"""
E2E tests for data isolation between households.
Critical security tests to ensure users can't access other households' data.
"""
import pytest
from conftest import BASE_URL, TEST_USERS


pytestmark = pytest.mark.integration


class TestTransactionIsolation:
    """Transaction data isolation tests."""

    def test_alice_sees_only_her_household_transactions(self, page, setup_two_households, login_as):
        """Alice should only see Alice & Bob household transactions."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Should see Alice & Bob transactions
        assert 'Grocery Store' in content or 'Restaurant' in content

        # Should NOT see Charlie & Diana transactions
        assert 'Electronics Store' not in content
        assert 'Gas Station' not in content

    def test_charlie_sees_only_his_household_transactions(self, page, setup_two_households, login_as):
        """Charlie should only see Charlie & Diana household transactions."""
        login_as('charlie')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Should see Charlie & Diana transactions
        assert 'Electronics Store' in content or 'Gas Station' in content

        # Should NOT see Alice & Bob transactions
        assert 'Grocery Store' not in content
        assert 'Restaurant' not in content

    def test_bob_sees_same_as_alice(self, page, setup_two_households, login_as):
        """Bob should see same transactions as Alice (same household)."""
        login_as('bob')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Should see Alice & Bob transactions
        assert 'Grocery Store' in content or 'Restaurant' in content

        # Should NOT see Charlie & Diana transactions
        assert 'Electronics Store' not in content
        assert 'Gas Station' not in content


class TestReconciliationIsolation:
    """Reconciliation data isolation tests."""

    def test_alice_reconciliation_shows_correct_members(self, page, setup_two_households, login_as):
        """Alice's reconciliation should show Alice & Bob, not Charlie & Diana."""
        login_as('alice')

        page.goto(f"{BASE_URL}/reconciliation")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Should show Alice & Bob
        assert 'Alice' in content or 'Bob' in content

        # Should NOT show Charlie & Diana
        assert 'Charlie' not in content
        assert 'Diana' not in content

    def test_charlie_reconciliation_shows_correct_members(self, page, setup_two_households, login_as):
        """Charlie's reconciliation should show Charlie & Diana, not Alice & Bob."""
        login_as('charlie')

        page.goto(f"{BASE_URL}/reconciliation")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Should show Charlie & Diana
        assert 'Charlie' in content or 'Diana' in content

        # Should NOT show Alice & Bob
        assert 'Alice' not in content
        assert 'Bob' not in content


class TestSettingsIsolation:
    """Household settings isolation tests."""

    def test_alice_settings_shows_her_household(self, page, setup_two_households, login_as):
        """Alice should see her household in settings, not others."""
        login_as('alice')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Should see Alice & Bob household
        assert 'Alice' in content and 'Bob' in content

        # Should NOT see Charlie & Diana
        assert 'Charlie' not in content
        assert 'Diana' not in content

    def test_charlie_settings_shows_his_household(self, page, setup_two_households, login_as):
        """Charlie should see his household in settings, not others."""
        login_as('charlie')

        page.goto(f"{BASE_URL}/household/settings")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Should see Charlie & Diana household
        assert 'Charlie' in content and 'Diana' in content

        # Should NOT see Alice & Bob
        assert 'Alice' not in content
        assert 'Bob' not in content


class TestFormDropdownIsolation:
    """Form dropdown data isolation tests."""

    def test_paid_by_dropdown_shows_only_household_members(self, page, setup_two_households, login_as):
        """Paid By dropdown should only show current household members."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        paid_by_select = page.locator('select[name="paid_by"]')
        if paid_by_select.count() > 0:
            options_text = paid_by_select.first.inner_text()

            # Should have Alice and Bob
            assert 'Alice' in options_text or 'Bob' in options_text

            # Should NOT have Charlie or Diana
            assert 'Charlie' not in options_text
            assert 'Diana' not in options_text


class TestDirectURLAccess:
    """Tests for direct URL manipulation attempts."""

    def test_cannot_access_other_household_by_id(self, page, setup_two_households, login_as, app):
        """User cannot access another household by manipulating URLs."""
        from models import Household

        # Get Charlie's household ID
        with app.app_context():
            charlie_household = Household.query.filter_by(name='Charlie & Diana Household').first()
            charlie_hh_id = charlie_household.id

        # Login as Alice
        login_as('alice')

        # Try to switch to Charlie's household
        page.goto(f"{BASE_URL}/household/switch/{charlie_hh_id}")
        page.wait_for_load_state('networkidle')

        # Should not have access - redirected or error
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()
        # Should still see Alice's data, not Charlie's
        assert 'Electronics Store' not in content
        assert 'Gas Station' not in content


class TestDatabaseIsolation:
    """Database-level isolation verification."""

    def test_transactions_filtered_by_household(self, app, setup_two_households):
        """Verify transactions are properly filtered at database level."""
        from models import Transaction, Household

        with app.app_context():
            h1 = Household.query.filter_by(name='Alice & Bob Household').first()
            h2 = Household.query.filter_by(name='Charlie & Diana Household').first()

            h1_transactions = Transaction.query.filter_by(household_id=h1.id).all()
            h2_transactions = Transaction.query.filter_by(household_id=h2.id).all()

            # Each household should have its own transactions
            h1_merchants = [t.merchant for t in h1_transactions]
            h2_merchants = [t.merchant for t in h2_transactions]

            assert 'Grocery Store' in h1_merchants or 'Restaurant' in h1_merchants
            assert 'Electronics Store' in h2_merchants or 'Gas Station' in h2_merchants

            # No overlap
            assert 'Electronics Store' not in h1_merchants
            assert 'Grocery Store' not in h2_merchants

    def test_users_can_belong_to_multiple_households(self, app, db, setup_two_households):
        """Verify a user can belong to multiple households."""
        from models import User, Household, HouseholdMember

        with app.app_context():
            alice = User.query.filter_by(email=TEST_USERS['alice']['email']).first()
            h2 = Household.query.filter_by(name='Charlie & Diana Household').first()

            # Add Alice to second household
            member = HouseholdMember(
                household_id=h2.id,
                user_id=alice.id,
                role='member',
                display_name='Alice Guest'
            )
            db.session.add(member)
            db.session.commit()

            # Verify Alice is in both
            alice_memberships = HouseholdMember.query.filter_by(user_id=alice.id).all()
            assert len(alice_memberships) == 2

            # Cleanup
            db.session.delete(member)
            db.session.commit()


class TestNoDataLeakage:
    """Tests to ensure no data leakage between sessions."""

    def test_logout_clears_household_context(self, page, setup_two_households, login_as, logout):
        """Logging out should clear household context."""
        login_as('alice')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        # Verify Alice sees her data
        assert 'Grocery Store' in page.content() or 'Restaurant' in page.content()

        # Logout
        logout()

        # Login as Charlie
        login_as('charlie')

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')

        content = page.content()

        # Charlie should see his data only
        assert 'Electronics Store' in content or 'Gas Station' in content
        assert 'Grocery Store' not in content
        assert 'Restaurant' not in content
