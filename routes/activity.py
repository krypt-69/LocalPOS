from flask import Blueprint, render_template, request
from flask_login import login_required
from database.models import db, ActivityLog, User
from utils.role_helpers import role_required
from datetime import datetime, timedelta

activity_bp = Blueprint('activity', __name__, url_prefix='/activity')

@activity_bp.route('/')
@login_required
@role_required('owner')
def view_log():
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action', '')
    days = request.args.get('days', type=int, default=7)
    start_date = datetime.now() - timedelta(days=days)
    query = ActivityLog.query.filter(ActivityLog.created_at >= start_date)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter(ActivityLog.action.ilike(f'%{action}%'))
    logs = query.order_by(ActivityLog.created_at.desc()).all()
    users = User.query.all()
    return render_template('activity_log.html', logs=logs, users=users, selected_user=user_id, selected_action=action, days=days)
