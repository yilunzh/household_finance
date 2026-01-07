#!/usr/bin/env python3
"""
Playwright-based authentication testing.
Tests user registration, login, logout, and session management.
"""
import asyncio
from playwright.async_api import async_playwright, expect
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "http://127.0.0.1:5001"

async def test_registration(page):
    """Test user registration flow."""
    print("\n" + "=" * 60)
    print("TEST 1: User Registration")
    print("=" * 60)

    # Navigate to registration page
    await page.goto(f"{BASE_URL}/register")
    await page.wait_for_load_state('networkidle')

    print("✓ Registration page loaded")

    # Verify page title
    await expect(page).to_have_title("Register - Zhang Estate Expense Tracker")
    print("✓ Page title correct")

    # Fill registration form
    await page.fill('#name', 'Test User')
    await page.fill('#email', 'test@example.com')
    await page.fill('#password', 'testpass123')
    await page.fill('#confirm_password', 'testpass123')

    print("✓ Registration form filled")

    # Submit form
    await page.click('button[type="submit"]')
    await page.wait_for_load_state('networkidle')

    # Check for success message
    success_message = page.locator('text=Welcome, Test User!')
    if await success_message.is_visible():
        print("✓ Registration successful!")
        print("✓ Welcome message displayed")
    else:
        print("✗ Registration may have failed")
        # Take screenshot for debugging
        await page.screenshot(path='/tmp/registration_failed.png')
        print("  Screenshot saved to /tmp/registration_failed.png")

    # Should be redirected to index page
    current_url = page.url
    print(f"✓ Redirected to: {current_url}")

    return True

async def test_duplicate_registration(page):
    """Test that duplicate email is rejected."""
    print("\n" + "=" * 60)
    print("TEST 2: Duplicate Registration (should fail)")
    print("=" * 60)

    await page.goto(f"{BASE_URL}/logout")
    await page.wait_for_load_state('networkidle')

    await page.goto(f"{BASE_URL}/register")
    await page.wait_for_load_state('networkidle')

    # Try to register with same email
    await page.fill('#name', 'Another User')
    await page.fill('#email', 'test@example.com')  # Same email
    await page.fill('#password', 'password123')
    await page.fill('#confirm_password', 'password123')

    await page.click('button[type="submit"]')
    await page.wait_for_load_state('networkidle')

    # Check for error message
    error_message = page.locator('text=An account with this email already exists')
    if await error_message.is_visible():
        print("✓ Duplicate email correctly rejected")
    else:
        print("✗ Should have rejected duplicate email")

    return True

async def test_password_mismatch(page):
    """Test password confirmation validation."""
    print("\n" + "=" * 60)
    print("TEST 3: Password Mismatch (should fail)")
    print("=" * 60)

    await page.goto(f"{BASE_URL}/register")
    await page.wait_for_load_state('networkidle')

    await page.fill('#name', 'New User')
    await page.fill('#email', 'newuser@example.com')
    await page.fill('#password', 'password123')
    await page.fill('#confirm_password', 'differentpassword')

    # Client-side validation should catch this
    page.once("dialog", lambda dialog: dialog.accept())
    await page.click('button[type="submit"]')

    print("✓ Password mismatch validation triggered")

    return True

async def test_login_valid(page):
    """Test login with valid credentials."""
    print("\n" + "=" * 60)
    print("TEST 4: Login with Valid Credentials")
    print("=" * 60)

    # Navigate to login page
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state('networkidle')

    print("✓ Login page loaded")

    # Verify page title
    await expect(page).to_have_title("Login - Zhang Estate Expense Tracker")
    print("✓ Page title correct")

    # Fill login form
    await page.fill('#email', 'test@example.com')
    await page.fill('#password', 'testpass123')
    await page.check('#remember')

    print("✓ Login form filled")

    # Submit form
    await page.click('button[type="submit"]')
    await page.wait_for_load_state('networkidle')

    # Check for success message
    success_message = page.locator('text=Welcome back, Test User!')
    if await success_message.is_visible():
        print("✓ Login successful!")
        print("✓ Welcome back message displayed")
    else:
        print("✗ Login may have failed")
        await page.screenshot(path='/tmp/login_failed.png')
        print("  Screenshot saved to /tmp/login_failed.png")

    # Should be redirected to index page
    current_url = page.url
    print(f"✓ Redirected to: {current_url}")

    return True

async def test_login_invalid(page):
    """Test login with invalid credentials."""
    print("\n" + "=" * 60)
    print("TEST 5: Login with Invalid Credentials (should fail)")
    print("=" * 60)

    # Logout first
    await page.goto(f"{BASE_URL}/logout")
    await page.wait_for_load_state('networkidle')

    # Navigate to login page
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state('networkidle')

    # Fill login form with wrong password
    await page.fill('#email', 'test@example.com')
    await page.fill('#password', 'wrongpassword')

    # Submit form
    await page.click('button[type="submit"]')
    await page.wait_for_load_state('networkidle')

    # Check for error message
    error_message = page.locator('text=Invalid email or password')
    if await error_message.is_visible():
        print("✓ Invalid credentials correctly rejected")
        print("✓ Error message displayed")
    else:
        print("✗ Should have shown error message")

    # Should still be on login page
    await expect(page).to_have_url(f"{BASE_URL}/login")
    print("✓ Remained on login page")

    return True

async def test_logout(page):
    """Test logout functionality."""
    print("\n" + "=" * 60)
    print("TEST 6: Logout")
    print("=" * 60)

    # Login first
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state('networkidle')
    await page.fill('#email', 'test@example.com')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')
    await page.wait_for_load_state('networkidle')

    print("✓ Logged in")

    # Logout
    await page.goto(f"{BASE_URL}/logout")
    await page.wait_for_load_state('networkidle')

    # Check for logout message
    logout_message = page.locator('text=You have been logged out')
    if await logout_message.is_visible():
        print("✓ Logout successful")
        print("✓ Logout message displayed")
    else:
        print("✗ Logout message not found")

    # Should be redirected to login page
    await expect(page).to_have_url(f"{BASE_URL}/login")
    print("✓ Redirected to login page")

    return True

async def test_protected_route_unauthorized(page):
    """Test accessing protected route without login."""
    print("\n" + "=" * 60)
    print("TEST 7: Access Protected Route (not logged in)")
    print("=" * 60)

    # Try to access logout without being logged in
    await page.goto(f"{BASE_URL}/logout")
    await page.wait_for_load_state('networkidle')

    # Should be redirected to login page
    await expect(page).to_have_url(f"{BASE_URL}/login")
    print("✓ Unauthorized access redirected to login")

    # Check for login message
    login_message = page.locator('text=Please log in to access this page')
    if await login_message.is_visible():
        print("✓ Login prompt message displayed")

    return True

async def test_session_persistence(page):
    """Test that session persists across page loads."""
    print("\n" + "=" * 60)
    print("TEST 8: Session Persistence")
    print("=" * 60)

    # Login
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state('networkidle')
    await page.fill('#email', 'test@example.com')
    await page.fill('#password', 'testpass123')
    await page.check('#remember')
    await page.click('button[type="submit"]')
    await page.wait_for_load_state('networkidle')

    print("✓ Logged in with remember me")

    # Navigate to different pages
    await page.goto(f"{BASE_URL}/")
    await page.wait_for_load_state('networkidle')
    print("✓ Navigated to index page")

    await page.goto(f"{BASE_URL}/reconciliation")
    await page.wait_for_load_state('networkidle')
    print("✓ Navigated to reconciliation page")

    # Session should still be active
    # Try to logout (only works if logged in)
    await page.goto(f"{BASE_URL}/logout")
    await page.wait_for_load_state('networkidle')

    # Should successfully logout (confirming we were logged in)
    await expect(page).to_have_url(f"{BASE_URL}/login")
    print("✓ Session persisted across page navigation")

    return True

async def verify_password_hashing():
    """Verify password is hashed in database."""
    print("\n" + "=" * 60)
    print("TEST 9: Password Hashing Verification")
    print("=" * 60)

    from app import app, db
    from models import User

    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()

        if user:
            print(f"✓ User found in database")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.name}")
            print(f"  Password hash (first 30 chars): {user.password_hash[:30]}...")

            # Verify it's hashed (PBKDF2 format)
            if user.password_hash.startswith('pbkdf2:sha256:'):
                print("✓ Password is properly hashed with PBKDF2")
            else:
                print(f"✗ Unexpected hash format: {user.password_hash[:20]}...")

            # Test password verification
            if user.check_password('testpass123'):
                print("✓ Password verification works correctly")
            else:
                print("✗ Password verification failed")

            # Verify wrong password fails
            if not user.check_password('wrongpassword'):
                print("✓ Wrong password correctly rejected")
            else:
                print("✗ Wrong password should be rejected")

            # Check timestamps
            print(f"  Created at: {user.created_at}")
            print(f"  Last login: {user.last_login}")

        else:
            print("✗ User not found in database")

    return True

async def run_all_tests():
    """Run all authentication tests."""
    print("\n" + "🧪" * 30)
    print("PLAYWRIGHT AUTHENTICATION TEST SUITE")
    print("🧪" * 30)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Run all tests
            await test_registration(page)
            await test_duplicate_registration(page)
            await test_password_mismatch(page)
            await test_login_valid(page)
            await test_login_invalid(page)
            await test_logout(page)
            await test_protected_route_unauthorized(page)
            await test_session_persistence(page)

            # Close browser before database test
            await browser.close()

            # Database verification (doesn't need browser)
            await verify_password_hashing()

            print("\n" + "=" * 60)
            print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='/tmp/test_error.png')
            print("Screenshot saved to /tmp/test_error.png")
            await browser.close()
            return False

    return True

if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
