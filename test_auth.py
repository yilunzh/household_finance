#!/usr/bin/env python3
"""
Quick authentication testing script.
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5001"

def test_registration():
    """Test user registration."""
    print("=" * 60)
    print("TEST 1: User Registration")
    print("=" * 60)

    # Get CSRF token from registration page
    session = requests.Session()
    response = session.get(f"{BASE_URL}/register")
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

    print(f"✓ Registration page loaded")
    print(f"✓ CSRF token obtained: {csrf_token[:20]}...")

    # Register new user
    data = {
        'csrf_token': csrf_token,
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'testpass123',
        'confirm_password': 'testpass123'
    }

    response = session.post(f"{BASE_URL}/register", data=data, allow_redirects=False)

    if response.status_code == 302:  # Redirect after successful registration
        print(f"✓ User registered successfully!")
        print(f"✓ Redirected to: {response.headers.get('Location', 'N/A')}")
        return session
    else:
        print(f"✗ Registration failed with status: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        flash_messages = soup.find_all('div', class_='rounded-lg')
        for msg in flash_messages:
            print(f"  Message: {msg.get_text(strip=True)}")
        return None

def test_login():
    """Test user login."""
    print("\n" + "=" * 60)
    print("TEST 2: User Login")
    print("=" * 60)

    # Create new session (simulating new browser)
    session = requests.Session()
    response = session.get(f"{BASE_URL}/login")
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

    print(f"✓ Login page loaded")
    print(f"✓ CSRF token obtained: {csrf_token[:20]}...")

    # Login with registered user
    data = {
        'csrf_token': csrf_token,
        'email': 'test@example.com',
        'password': 'testpass123',
        'remember': 'on'
    }

    response = session.post(f"{BASE_URL}/login", data=data, allow_redirects=False)

    if response.status_code == 302:
        print(f"✓ Login successful!")
        print(f"✓ Redirected to: {response.headers.get('Location', 'N/A')}")

        # Check if session cookie is set
        if 'session' in session.cookies:
            print(f"✓ Session cookie set")

        return session
    else:
        print(f"✗ Login failed with status: {response.status_code}")
        return None

def test_invalid_login():
    """Test login with invalid credentials."""
    print("\n" + "=" * 60)
    print("TEST 3: Invalid Login (should fail)")
    print("=" * 60)

    session = requests.Session()
    response = session.get(f"{BASE_URL}/login")
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

    # Try login with wrong password
    data = {
        'csrf_token': csrf_token,
        'email': 'test@example.com',
        'password': 'wrongpassword'
    }

    response = session.post(f"{BASE_URL}/login", data=data)

    if 'Invalid email or password' in response.text:
        print(f"✓ Invalid credentials correctly rejected")
        return True
    else:
        print(f"✗ Should have rejected invalid credentials")
        return False

def test_protected_route(session):
    """Test accessing a protected route."""
    print("\n" + "=" * 60)
    print("TEST 4: Access Protected Route (logout)")
    print("=" * 60)

    if session is None:
        print("✗ No valid session available")
        return

    # Try to access logout (requires login)
    response = session.get(f"{BASE_URL}/logout", allow_redirects=False)

    if response.status_code == 302:
        print(f"✓ Logout successful!")
        print(f"✓ Redirected to: {response.headers.get('Location', 'N/A')}")
    else:
        print(f"✗ Logout failed with status: {response.status_code}")

def test_logout_without_login():
    """Test accessing logout without being logged in."""
    print("\n" + "=" * 60)
    print("TEST 5: Logout Without Login (should redirect)")
    print("=" * 60)

    # New session (not logged in)
    session = requests.Session()
    response = session.get(f"{BASE_URL}/logout", allow_redirects=False)

    if response.status_code == 302 and 'login' in response.headers.get('Location', ''):
        print(f"✓ Correctly redirected to login page")
        print(f"✓ Location: {response.headers.get('Location', 'N/A')}")
    else:
        print(f"✗ Should have redirected to login")

def test_password_hashing():
    """Check that password is hashed in database."""
    print("\n" + "=" * 60)
    print("TEST 6: Password Hashing in Database")
    print("=" * 60)

    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    from app import app, db
    from models import User

    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        if user:
            print(f"✓ User found in database: {user.email}")
            print(f"✓ Name: {user.name}")
            print(f"✓ Password hash (first 30 chars): {user.password_hash[:30]}...")

            # Verify password hash is not plaintext
            if user.password_hash.startswith('pbkdf2:sha256:'):
                print(f"✓ Password is properly hashed (PBKDF2)")
            else:
                print(f"✗ Password hash format unexpected")

            # Test password verification
            if user.check_password('testpass123'):
                print(f"✓ Password verification works correctly")
            else:
                print(f"✗ Password verification failed")
        else:
            print(f"✗ User not found in database")

if __name__ == '__main__':
    try:
        # Install beautifulsoup4 if needed
        import subprocess
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("Installing beautifulsoup4...")
            subprocess.check_call(['pip', 'install', 'beautifulsoup4'])
            from bs4 import BeautifulSoup

        print("\n🧪 AUTHENTICATION TESTING SUITE")
        print("=" * 60)

        # Run tests
        session = test_registration()
        test_login()
        test_invalid_login()
        if session:
            test_protected_route(session)
        test_logout_without_login()
        test_password_hashing()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
