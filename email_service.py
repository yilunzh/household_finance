"""
Email service for sending household invitations.
"""
import os
from flask import current_app, render_template, url_for
from flask_mail import Mail, Message

# Initialize Flask-Mail (will be configured by app)
mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with app configuration."""
    # Mail server configuration from environment variables
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@household-tracker.com')

    # Suppress email sending in development if not configured
    app.config['MAIL_SUPPRESS_SEND'] = not app.config.get('MAIL_USERNAME')

    mail.init_app(app)
    return mail


def send_invitation_email(invitation, household, inviter):
    """
    Send an invitation email to join a household.

    Args:
        invitation: Invitation model instance
        household: Household model instance
        inviter: User model instance (who sent the invitation)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Build the invitation URL
        # Use SITE_URL environment variable in production, fallback to localhost
        site_url = os.environ.get('SITE_URL', 'http://localhost:5001')
        invite_url = f"{site_url}/invite/accept?token={invitation.token}"

        # Create the email message
        subject = f"{inviter.name} invited you to join {household.name} on Lucky Ledger"

        # Build HTML body
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #3b82f6; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }}
        .button {{ display: inline-block; background: #3b82f6; color: white !important; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
        .button:hover {{ background: #2563eb; }}
        .footer {{ padding: 20px; font-size: 12px; color: #6b7280; text-align: center; }}
        .expires {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 10px; border-radius: 4px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Lucky Ledger</h1>
        </div>
        <div class="content">
            <h2>You're invited!</h2>
            <p><strong>{inviter.name}</strong> has invited you to join their household <strong>"{household.name}"</strong> on Lucky Ledger.</p>
            <p>Lucky Ledger helps couples and roommates track shared expenses and calculate who owes what at the end of each month.</p>
            <p>Click the button below to accept the invitation:</p>
            <a href="{invite_url}" class="button">Accept Invitation</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #3b82f6;">{invite_url}</p>
            <div class="expires">
                <strong>Note:</strong> This invitation expires in 7 days.
            </div>
        </div>
        <div class="footer">
            <p>If you didn't expect this invitation, you can safely ignore this email.</p>
            <p>Lucky Ledger - Track expenses together</p>
        </div>
    </div>
</body>
</html>
"""

        # Plain text version
        text_body = f"""
{inviter.name} invited you to join {household.name} on Lucky Ledger

Lucky Ledger helps couples and roommates track shared expenses and calculate who owes what at the end of each month.

Click the link below to accept the invitation:
{invite_url}

Note: This invitation expires in 7 days.

If you didn't expect this invitation, you can safely ignore this email.
"""

        # Create and send the message
        msg = Message(
            subject=subject,
            recipients=[invitation.email],
            body=text_body,
            html=html_body
        )

        # Check if mail sending is suppressed (development without SMTP config)
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            print(f"[EMAIL SUPPRESSED] Would send invitation to: {invitation.email}")
            print(f"[EMAIL SUPPRESSED] Invitation URL: {invite_url}")
            return True

        mail.send(msg)
        print(f"[EMAIL] Invitation sent to: {invitation.email}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send invitation: {e}")
        import traceback
        traceback.print_exc()
        return False


def is_mail_configured():
    """Check if email is properly configured."""
    return bool(os.environ.get('MAIL_USERNAME'))
