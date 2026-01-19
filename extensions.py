"""
Flask extensions instantiated without app binding.

These are initialized later in create_app() to support the application factory pattern.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

# Database
db = SQLAlchemy()

# CSRF Protection
csrf = CSRFProtect()

# Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Rate Limiter (will be configured with app)
limiter = Limiter(key_func=get_remote_address)

# Mail
mail = Mail()
