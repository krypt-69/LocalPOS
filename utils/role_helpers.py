"""Role-based permission helpers and decorators."""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*allowed_roles):
    """Decorator to restrict access to certain roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in allowed_roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard.dashboard_home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_permission(permission_name):
    """Placeholder for future granular permission system.
    Currently uses role-based logic."""
    role_permissions = {
        'owner': ['*'],
        'admin': ['*'],
        'worker': ['sell', 'create_credit_sale', 'record_payment', 'view_services', 'create_service']
    }
    if current_user.role == 'owner' or current_user.role == 'admin':
        return True
    return permission_name in role_permissions.get(current_user.role, [])
