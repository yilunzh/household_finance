"""
Authentication routes: register, login, logout, password reset.
"""
import logging
import secrets
from datetime import datetime, timedelta

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required

from extensions import db, limiter
from models import User
from email_service import send_password_reset_email
from blueprints.auth import auth_bp

logger = logging.getLogger(__name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    """User registration page."""
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('transactions.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()

        print(f"[DEBUG] Registration attempt: email={email}, name={name}")

        # Validation
        if not email or not password or not name:
            print("[DEBUG] Validation failed: missing fields")
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register.html')

        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)

        try:
            print("[DEBUG] Attempting to save user to database...")
            db.session.add(user)
            db.session.commit()
            print("[DEBUG] User saved successfully!")

            # Auto-login after registration
            login_user(user, remember=True)
            print("[DEBUG] User logged in successfully!")

            flash(f'Welcome, {user.name}! Your account has been created.', 'success')
            return redirect(url_for('transactions.index'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            print(f'[ERROR] Registration error: {e}')
            import traceback
            traceback.print_exc()
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    """User login page."""
    # If user is already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('transactions.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'

        # Validation
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check password
        if user is None or not user.check_password(password):
            logger.warning(f"Failed login attempt for email: {email} from IP: {request.remote_addr}")
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        # Check if account is active
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'danger')
            return render_template('auth/login.html')

        # Login user
        login_user(user, remember=remember)
        logger.info(f"Successful login for user: {user.email} (ID: {user.id}) from IP: {request.remote_addr}")

        # Update last login timestamp
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Handle 'next' parameter for redirect
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page)

        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('transactions.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per minute", methods=["POST"])
def forgot_password():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('transactions.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('auth/forgot_password.html')

        # Find user - but don't reveal if they exist
        user = User.query.filter_by(email=email).first()

        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # Send email
            send_password_reset_email(user, token)
            logger.info(f"Password reset requested for: {email}")

        # Always show success message (don't reveal if email exists)
        return render_template('auth/reset_sent.html', email=email)

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('transactions.index'))

    # Find user by token
    user = User.query.filter_by(password_reset_token=token).first()

    # Check if token is valid and not expired
    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        flash('This password reset link is invalid or has expired.', 'danger')
        return render_template('auth/reset_invalid.html')

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not password or not confirm_password:
            flash('Please fill in all fields.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/reset_password.html', token=token)

        # Update password and clear token
        user.set_password(password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()

        logger.info(f"Password reset completed for user: {user.email}")
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
