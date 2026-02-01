"""
Cleanup service for scheduled maintenance tasks.

Handles:
- Expired import session cleanup
- Audit log retention
- Orphaned file cleanup
"""
import logging
from datetime import datetime, timedelta

from extensions import db
from models import ImportSession, ImportAuditLog
from services.import_service import delete_session_files

logger = logging.getLogger(__name__)


def cleanup_expired_sessions(days=7):
    """Clean up old incomplete import sessions.

    Removes sessions that have been in pending/processing/ready/failed state
    for longer than the specified number of days. Also securely deletes
    any associated source files.

    Note: This is a global cleanup (no household_id filter) because:
    - ImportSession is user-scoped (user_id), not household-scoped
    - This is a system maintenance task, not a user-facing query
    - Each user's sessions are cleaned independently by status/age

    Args:
        days: Number of days after which to clean up incomplete sessions.

    Returns:
        Number of sessions cleaned up.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Global query across all users - intentional for maintenance task
    # ImportSession uses user_id scoping, not household_id
    expired_sessions = ImportSession.query.filter(
        ImportSession.status.in_([
            ImportSession.STATUS_PENDING,
            ImportSession.STATUS_PROCESSING,
            ImportSession.STATUS_READY,
            ImportSession.STATUS_FAILED
        ]),
        ImportSession.created_at < cutoff
    ).all()

    count = 0
    for session in expired_sessions:
        try:
            # Delete source files securely
            delete_session_files(session)
            # Delete session (cascades to extracted transactions)
            db.session.delete(session)
            count += 1
            logger.info(f"Cleaned up expired session {session.id}")
        except Exception as e:
            logger.error(f"Failed to cleanup session {session.id}: {e}")
            db.session.rollback()

    if count > 0:
        db.session.commit()
        logger.info(f"Cleaned up {count} expired import sessions")

    return count


def cleanup_old_audit_logs(days=90):
    """Delete audit logs older than retention period.

    Note: This is a global cleanup (no household_id filter) because:
    - ImportAuditLog is scoped by session_id, which links to user_id
    - This is a system maintenance task for log retention compliance
    - Deleting old logs system-wide is the intended behavior

    Args:
        days: Number of days to retain audit logs.

    Returns:
        Number of audit logs deleted.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Global bulk delete for efficiency - intentional for maintenance task
    # Audit logs are retention-based, not user-isolated
    count = ImportAuditLog.query.filter(
        ImportAuditLog.created_at < cutoff
    ).delete(synchronize_session=False)

    db.session.commit()

    if count > 0:
        logger.info(f"Cleaned up {count} old audit logs (older than {days} days)")

    return count


def run_daily_cleanup():
    """Run all daily cleanup tasks.

    This is the main entry point called by the scheduler.
    """
    from flask import current_app

    logger.info("Starting daily cleanup tasks")

    with current_app.app_context():
        # Cleanup expired sessions (7 days old)
        sessions_cleaned = cleanup_expired_sessions(days=7)

        # Cleanup old audit logs (90 days retention)
        logs_cleaned = cleanup_old_audit_logs(days=90)

        logger.info(
            f"Daily cleanup complete: {sessions_cleaned} sessions, "
            f"{logs_cleaned} audit logs"
        )

    return {
        'sessions_cleaned': sessions_cleaned,
        'logs_cleaned': logs_cleaned
    }


def run_cleanup_with_app(app, sessions_days=7, audit_days=90, run_all=False):
    """Run cleanup tasks with a specific Flask app context.

    Used by CLI commands where we need to pass the app explicitly.

    Args:
        app: Flask application instance.
        sessions_days: Days after which to cleanup sessions (0 to skip).
        audit_days: Days after which to cleanup audit logs (0 to skip).
        run_all: If True, run all cleanup tasks with default settings.

    Returns:
        Dict with cleanup results.
    """
    results = {
        'sessions_cleaned': 0,
        'logs_cleaned': 0
    }

    with app.app_context():
        if run_all or sessions_days > 0:
            days = sessions_days if sessions_days > 0 else 7
            results['sessions_cleaned'] = cleanup_expired_sessions(days=days)

        if run_all or audit_days > 0:
            days = audit_days if audit_days > 0 else 90
            results['logs_cleaned'] = cleanup_old_audit_logs(days=days)

    return results
