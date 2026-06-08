from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from database.models import db, User
from utils.role_helpers import role_required
from utils.activity_logger import log_activity

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@login_required
@role_required('owner')
def list_users():
    users = User.query.order_by(User.created_at).all()
    return render_template('users_list.html', users=users)

@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('owner')
def new_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'worker')
        if not username or not password or not full_name:
            flash('All fields are required.', 'danger')
            return redirect(url_for('users.new_user'))
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash(f'Username "{username}" already exists.', 'danger')
            return redirect(url_for('users.new_user'))
        user = User(username=username, password_hash=generate_password_hash(password), full_name=full_name, role=role, is_active=True)
        db.session.add(user)
        db.session.commit()
        log_activity('user_create', f"Created user {username} with role {role}", 'user', user.id)
        flash(f'User "{username}" created successfully.', 'success')
        return redirect(url_for('users.list_users'))
    return render_template('user_form.html', title='Create User', user=None)

@users_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('owner')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id and request.method == 'POST':
        flash('You cannot change your own role or status here. Use another owner account.', 'warning')
        return redirect(url_for('users.list_users'))
    if request.method == 'POST':
        old_role = user.role
        old_active = user.is_active
        user.full_name = request.form.get('full_name', '').strip()
        user.role = request.form.get('role', 'worker')
        user.is_active = request.form.get('is_active') == 'on'
        new_password = request.form.get('password', '').strip()
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            flash('Password updated.', 'success')
        db.session.commit()
        if old_role != user.role:
            log_activity('user_role_change', f"Changed role of {user.username} from {old_role} to {user.role}", 'user', user.id)
        if old_active != user.is_active:
            log_activity('user_status_change', f"{'Activated' if user.is_active else 'Deactivated'} user {user.username}", 'user', user.id)
        flash(f'User "{user.username}" updated.', 'success')
        return redirect(url_for('users.list_users'))
    return render_template('user_form.html', title='Edit User', user=user)

@users_bp.route('/delete/<int:user_id>', methods=['POST'])
@login_required
@role_required('owner')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('users.list_users'))
    owner_count = User.query.filter_by(role='owner').count()
    if user.role == 'owner' and owner_count <= 1:
        flash('Cannot delete the only owner account.', 'danger')
        return redirect(url_for('users.list_users'))
    db.session.delete(user)
    db.session.commit()
    log_activity('user_delete', f"Deleted user {user.username}", 'user', user_id)
    flash(f'User "{user.username}" deleted.', 'success')
    return redirect(url_for('users.list_users'))
