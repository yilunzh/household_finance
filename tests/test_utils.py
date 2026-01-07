"""
Unit tests for utility functions.
Tests reconciliation calculation, currency conversion, and settlement formatting.
"""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import date


pytestmark = pytest.mark.unit


class TestGetExchangeRate:
    """Tests for get_exchange_rate function."""

    def test_same_currency_returns_one(self):
        """Same currency should return 1.0 without API call."""
        from utils import get_exchange_rate

        rate = get_exchange_rate('USD', 'USD', '2024-01-15')
        assert rate == 1.0

        rate = get_exchange_rate('CAD', 'CAD', date(2024, 1, 15))
        assert rate == 1.0

    @patch('utils.requests.get')
    def test_api_success(self, mock_get):
        """Should return rate from API on success."""
        from utils import get_exchange_rate, _rate_cache

        # Clear cache
        _rate_cache.clear()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'rates': {'USD': 0.75}}
        mock_get.return_value = mock_response

        rate = get_exchange_rate('CAD', 'USD', '2024-01-15')

        assert rate == 0.75
        mock_get.assert_called_once()

    @patch('utils.requests.get')
    def test_caches_result(self, mock_get):
        """Should cache the result and not call API again."""
        from utils import get_exchange_rate, _rate_cache

        # Clear cache
        _rate_cache.clear()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'rates': {'USD': 0.72}}
        mock_get.return_value = mock_response

        # First call
        rate1 = get_exchange_rate('CAD', 'USD', '2024-02-20')
        # Second call (should use cache)
        rate2 = get_exchange_rate('CAD', 'USD', '2024-02-20')

        assert rate1 == 0.72
        assert rate2 == 0.72
        assert mock_get.call_count == 1  # Only called once

    @patch('utils.requests.get')
    def test_fallback_on_error(self, mock_get):
        """Should return fallback rate on API error."""
        from utils import get_exchange_rate, _rate_cache

        # Clear cache
        _rate_cache.clear()

        mock_get.side_effect = Exception("Network error")

        rate = get_exchange_rate('USD', 'CAD', '2024-01-15')

        # Fallback rate for USD->CAD is 1.4
        assert rate == 1.4

    def test_accepts_date_object(self):
        """Should accept date object and convert to string."""
        from utils import get_exchange_rate

        # Should not raise an error
        rate = get_exchange_rate('USD', 'USD', date(2024, 1, 15))
        assert rate == 1.0


class TestGetCurrentExchangeRate:
    """Tests for get_current_exchange_rate function."""

    def test_same_currency_returns_one(self):
        """Same currency should return 1.0."""
        from utils import get_current_exchange_rate

        assert get_current_exchange_rate('USD', 'USD') == 1.0

    @patch('utils.requests.get')
    def test_fallback_usd_to_cad(self, mock_get):
        """Should return 1.4 fallback for USD to CAD on error."""
        from utils import get_current_exchange_rate

        mock_get.side_effect = Exception("Network error")

        rate = get_current_exchange_rate('USD', 'CAD')
        assert rate == 1.4

    @patch('utils.requests.get')
    def test_fallback_other_currencies(self, mock_get):
        """Should return 1.0 fallback for other currency pairs on error."""
        from utils import get_current_exchange_rate

        mock_get.side_effect = Exception("Network error")

        rate = get_current_exchange_rate('EUR', 'GBP')
        assert rate == 1.0


class TestCalculateReconciliation:
    """Tests for calculate_reconciliation function."""

    def test_empty_transactions(self, app):
        """Empty transaction list should return zero balances."""
        from utils import calculate_reconciliation

        with app.app_context():
            # Create mock members
            class MockMember:
                def __init__(self, user_id, display_name):
                    self.user_id = user_id
                    self.display_name = display_name

            members = [
                MockMember(1, 'Alice'),
                MockMember(2, 'Bob')
            ]

            result = calculate_reconciliation([], members)

            assert result['user_payments'] == {1: 0.0, 2: 0.0}
            assert result['user_shares'] == {1: 0.0, 2: 0.0}
            assert result['settlement'] == "All settled up!"

    def test_shared_expense_50_50_split(self, app):
        """Shared expense should be split 50/50."""
        from utils import calculate_reconciliation

        with app.app_context():
            class MockMember:
                def __init__(self, user_id, display_name):
                    self.user_id = user_id
                    self.display_name = display_name

            class MockTransaction:
                def __init__(self, amount_in_usd, paid_by_user_id, category):
                    self.amount_in_usd = amount_in_usd
                    self.paid_by_user_id = paid_by_user_id
                    self.category = category

            members = [
                MockMember(1, 'Alice'),
                MockMember(2, 'Bob')
            ]

            # Alice pays $100 shared expense
            transactions = [
                MockTransaction(Decimal('100.00'), 1, 'SHARED')
            ]

            result = calculate_reconciliation(transactions, members)

            # Alice paid 100, owes 50, so she's owed 50
            # Bob paid 0, owes 50, so he owes 50
            assert result['user_payments'][1] == 100.0
            assert result['user_payments'][2] == 0.0
            assert result['user_shares'][1] == 50.0
            assert result['user_shares'][2] == 50.0
            assert result['user_balances'][1] == 50.0  # Alice is owed
            assert result['user_balances'][2] == -50.0  # Bob owes
            assert 'Bob owes Alice $50.00' in result['settlement']

    def test_i_pay_for_wife_category(self, app):
        """I_PAY_FOR_WIFE category should assign 100% to member 2."""
        from utils import calculate_reconciliation

        with app.app_context():
            class MockMember:
                def __init__(self, user_id, display_name):
                    self.user_id = user_id
                    self.display_name = display_name

            class MockTransaction:
                def __init__(self, amount_in_usd, paid_by_user_id, category):
                    self.amount_in_usd = amount_in_usd
                    self.paid_by_user_id = paid_by_user_id
                    self.category = category

            members = [
                MockMember(1, 'Alice'),
                MockMember(2, 'Bob')
            ]

            # Alice pays $80 for Bob
            transactions = [
                MockTransaction(Decimal('80.00'), 1, 'I_PAY_FOR_WIFE')
            ]

            result = calculate_reconciliation(transactions, members)

            # Alice paid 80, owes 0 (it's for Bob)
            # Bob paid 0, owes 80
            assert result['user_shares'][1] == 0.0
            assert result['user_shares'][2] == 80.0
            assert 'Bob owes Alice $80.00' in result['settlement']

    def test_wife_pays_for_me_category(self, app):
        """WIFE_PAYS_FOR_ME category should assign 100% to member 1."""
        from utils import calculate_reconciliation

        with app.app_context():
            class MockMember:
                def __init__(self, user_id, display_name):
                    self.user_id = user_id
                    self.display_name = display_name

            class MockTransaction:
                def __init__(self, amount_in_usd, paid_by_user_id, category):
                    self.amount_in_usd = amount_in_usd
                    self.paid_by_user_id = paid_by_user_id
                    self.category = category

            members = [
                MockMember(1, 'Alice'),
                MockMember(2, 'Bob')
            ]

            # Bob pays $60 for Alice
            transactions = [
                MockTransaction(Decimal('60.00'), 2, 'WIFE_PAYS_FOR_ME')
            ]

            result = calculate_reconciliation(transactions, members)

            # Alice paid 0, owes 60
            # Bob paid 60, owes 0
            assert result['user_shares'][1] == 60.0
            assert result['user_shares'][2] == 0.0
            assert 'Alice owes Bob $60.00' in result['settlement']

    def test_personal_expenses(self, app):
        """Personal expenses should only affect the person they're for."""
        from utils import calculate_reconciliation

        with app.app_context():
            class MockMember:
                def __init__(self, user_id, display_name):
                    self.user_id = user_id
                    self.display_name = display_name

            class MockTransaction:
                def __init__(self, amount_in_usd, paid_by_user_id, category):
                    self.amount_in_usd = amount_in_usd
                    self.paid_by_user_id = paid_by_user_id
                    self.category = category

            members = [
                MockMember(1, 'Alice'),
                MockMember(2, 'Bob')
            ]

            # Alice buys personal item for herself
            transactions = [
                MockTransaction(Decimal('50.00'), 1, 'PERSONAL_ME')
            ]

            result = calculate_reconciliation(transactions, members)

            # Alice paid 50, owes 50 (personal) -> balance 0
            assert result['user_payments'][1] == 50.0
            assert result['user_shares'][1] == 50.0
            assert result['user_balances'][1] == 0.0
            assert result['settlement'] == "All settled up!"

    def test_category_breakdown(self, app):
        """Should return correct category breakdown."""
        from utils import calculate_reconciliation

        with app.app_context():
            class MockMember:
                def __init__(self, user_id, display_name):
                    self.user_id = user_id
                    self.display_name = display_name

            class MockTransaction:
                def __init__(self, amount_in_usd, paid_by_user_id, category):
                    self.amount_in_usd = amount_in_usd
                    self.paid_by_user_id = paid_by_user_id
                    self.category = category

            members = [
                MockMember(1, 'Alice'),
                MockMember(2, 'Bob')
            ]

            transactions = [
                MockTransaction(Decimal('100.00'), 1, 'SHARED'),
                MockTransaction(Decimal('50.00'), 2, 'SHARED'),
                MockTransaction(Decimal('30.00'), 1, 'PERSONAL_ME')
            ]

            result = calculate_reconciliation(transactions, members)

            # Check breakdown
            breakdown = {item['category']: item for item in result['breakdown']}
            assert breakdown['SHARED']['count'] == 2
            assert breakdown['SHARED']['total'] == 150.0
            assert breakdown['PERSONAL_ME']['count'] == 1
            assert breakdown['PERSONAL_ME']['total'] == 30.0

    def test_member_names_returned(self, app):
        """Should return member_names mapping."""
        from utils import calculate_reconciliation

        with app.app_context():
            class MockMember:
                def __init__(self, user_id, display_name):
                    self.user_id = user_id
                    self.display_name = display_name

            members = [
                MockMember(1, 'Alice'),
                MockMember(2, 'Bob')
            ]

            result = calculate_reconciliation([], members)

            assert result['member_names'] == {1: 'Alice', 2: 'Bob'}


class TestFormatSettlementDynamic:
    """Tests for format_settlement_dynamic function."""

    def test_all_settled(self):
        """Should return 'All settled up!' when balances are zero."""
        from utils import format_settlement_dynamic

        result = format_settlement_dynamic(
            {1: 0.0, 2: 0.0},
            {1: 'Alice', 2: 'Bob'}
        )

        assert result == "All settled up!"

    def test_user1_owed_money(self):
        """Should show user2 owes user1 when user1 has positive balance."""
        from utils import format_settlement_dynamic

        result = format_settlement_dynamic(
            {1: 50.0, 2: -50.0},
            {1: 'Alice', 2: 'Bob'}
        )

        assert 'Bob owes Alice $50.00' in result

    def test_user2_owed_money(self):
        """Should show user1 owes user2 when user2 has positive balance."""
        from utils import format_settlement_dynamic

        result = format_settlement_dynamic(
            {1: -75.0, 2: 75.0},
            {1: 'Alice', 2: 'Bob'}
        )

        assert 'Alice owes Bob $75.00' in result

    def test_small_amount_threshold(self):
        """Amounts below threshold should be considered settled."""
        from utils import format_settlement_dynamic

        result = format_settlement_dynamic(
            {1: 0.005, 2: -0.005},
            {1: 'Alice', 2: 'Bob'}
        )

        assert result == "All settled up!"

    def test_non_two_person_household(self):
        """Should return message for non-2-person households."""
        from utils import format_settlement_dynamic

        result = format_settlement_dynamic(
            {1: 100.0, 2: -50.0, 3: -50.0},
            {1: 'Alice', 2: 'Bob', 3: 'Charlie'}
        )

        assert "2-person households only" in result
