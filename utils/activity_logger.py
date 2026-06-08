from flask_login import current_user
from flask import request
from database.models import db, ActivityLog
from datetime import datetime

def log_activity(action, details=None, target_type=None, target_id=None):
    """Log an activity for the current user."""
    try:
        if not current_user or not current_user.is_authenticated:
            return
        log = ActivityLog(
            user_id=current_user.id,
            username=current_user.username,
            action=action,
            details=details,
            target_type=target_type,
            target_id=target_id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # Fail silently – don't break business logic
        print(f"Failed to log activity: {e}")
