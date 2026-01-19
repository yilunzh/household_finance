"""
Configuration classes for Flask application.

Usage:
    from config import config
    app.config.from_object(config[config_name])
"""
import os
from datetime import timedelta


class Config:
    """Base configuration with defaults."""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Rate limiting (Flask-Limiter config keys)
    RATELIMIT_DEFAULT = "200 per day; 50 per hour"
    # Use Redis for persistent rate limiting if REDIS_URL is set, otherwise memory
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')

    # Mail configuration (optional - for invitations)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Site URL for email links
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5001')


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///database.db'
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    # Production: use /data directory which is mounted to persistent disk on Render
    # Note: 4 slashes = sqlite:// + absolute path /data/database.db
    SQLALCHEMY_DATABASE_URI = 'sqlite:////data/database.db'

    # Secure cookies in production (requires HTTPS)
    SESSION_COOKIE_SECURE = True

    # Content Security Policy
    CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self';"
    )


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}


def get_config_name():
    """Get configuration name from environment."""
    flask_env = os.environ.get('FLASK_ENV', 'development')
    if flask_env == 'production':
        return 'production'
    elif os.environ.get('TESTING'):
        return 'testing'
    return 'development'
