"""
E2E tests for CSV export functionality.
Tests export content and format.
"""
import pytest
from datetime import date
from conftest import BASE_URL


pytestmark = pytest.mark.integration


class TestExportAccess:
    """Export access tests."""

    def test_export_link_visible(self, page, setup_two_households, login_as):
        """Export link should be visible on reconciliation page."""
        login_as('alice')

        page.goto(f"{BASE_URL}/reconciliation")
        page.wait_for_load_state('networkidle')

        content = page.content().lower()
        # Should have export option
        assert 'export' in content or 'download' in content or 'csv' in content

    def test_export_requires_authentication(self, page, clean_test_data):
        """Export should require authentication."""
        current_month = date.today().strftime('%Y-%m')
        page.goto(f"{BASE_URL}/export/{current_month}")
        page.wait_for_load_state('networkidle')

        # Should redirect to login
        assert '/login' in page.url


class TestExportContent:
    """Export content tests."""

    def test_export_returns_csv(self, page, setup_two_households, login_as):
        """Export should return a CSV file."""
        login_as('alice')

        current_month = date.today().strftime('%Y-%m')

        # Use Playwright's download handler
        with page.expect_download() as download_info:
            page.goto(f"{BASE_URL}/export/{current_month}")

        download = download_info.value
        # Should be a CSV file
        assert 'csv' in download.suggested_filename.lower() or 'expense' in download.suggested_filename.lower()

    def test_export_contains_transactions(self, page, setup_two_households, login_as):
        """Exported CSV should contain transaction data."""
        login_as('alice')

        current_month = date.today().strftime('%Y-%m')

        with page.expect_download() as download_info:
            page.goto(f"{BASE_URL}/export/{current_month}")

        download = download_info.value
        path = download.path()

        # Read content
        with open(path, 'r') as f:
            content = f.read()

        # Should contain transaction data
        assert 'Grocery Store' in content or 'Restaurant' in content

    def test_export_contains_headers(self, page, setup_two_households, login_as):
        """Exported CSV should have column headers."""
        login_as('alice')

        current_month = date.today().strftime('%Y-%m')

        with page.expect_download() as download_info:
            page.goto(f"{BASE_URL}/export/{current_month}")

        download = download_info.value
        path = download.path()

        with open(path, 'r') as f:
            first_line = f.readline().lower()

        # Should have headers
        assert 'date' in first_line or 'merchant' in first_line or 'amount' in first_line

    def test_export_only_includes_household_data(self, page, setup_two_households, login_as):
        """Export should only include current household's data."""
        login_as('alice')

        current_month = date.today().strftime('%Y-%m')

        with page.expect_download() as download_info:
            page.goto(f"{BASE_URL}/export/{current_month}")

        download = download_info.value
        path = download.path()

        with open(path, 'r') as f:
            content = f.read()

        # Should have Alice's household data
        assert 'Grocery Store' in content or 'Restaurant' in content

        # Should NOT have Charlie's household data
        assert 'Electronics Store' not in content
        assert 'Gas Station' not in content


class TestExportFormat:
    """Export format tests."""

    def test_export_has_proper_filename(self, page, setup_two_households, login_as):
        """Export filename should include month."""
        login_as('alice')

        current_month = date.today().strftime('%Y-%m')

        with page.expect_download() as download_info:
            page.goto(f"{BASE_URL}/export/{current_month}")

        download = download_info.value
        filename = download.suggested_filename

        # Filename should be descriptive
        assert current_month in filename or 'expense' in filename.lower()

    def test_export_includes_summary(self, page, setup_two_households, login_as):
        """Export should include summary section."""
        login_as('alice')

        current_month = date.today().strftime('%Y-%m')

        with page.expect_download() as download_info:
            page.goto(f"{BASE_URL}/export/{current_month}")

        download = download_info.value
        path = download.path()

        with open(path, 'r') as f:
            content = f.read().lower()

        # Should have summary or total info
        assert 'total' in content or 'paid' in content or 'owes' in content or 'summary' in content
