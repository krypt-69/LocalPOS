from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.models import db, ServiceCategory, ServiceType, ServiceJob, ServiceHistory, Debtor, Payment
from utils.role_helpers import role_required
from utils.activity_logger import log_activity
from datetime import datetime, date
import re

services_bp = Blueprint('services', __name__, url_prefix='/services')

def generate_job_number():
    last = ServiceJob.query.order_by(ServiceJob.id.desc()).first()
    if not last:
        return 'SRV-000001'
    match = re.search(r'(\d+)$', last.job_number)
    if match:
        num = int(match.group(1)) + 1
        return f'SRV-{num:06d}'
    return 'SRV-000001'

@services_bp.route('/')
@login_required
def list_services():
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    query = ServiceJob.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(db.or_(ServiceJob.customer_name.ilike(f'%{search}%'), ServiceJob.job_number.ilike(f'%{search}%'), ServiceJob.item_description.ilike(f'%{search}%')))
    jobs = query.order_by(ServiceJob.created_at.desc()).all()
    return render_template('services_list.html', jobs=jobs, status_filter=status_filter, search=search)

@services_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_service():
    categories = ServiceCategory.query.all()
    service_types = ServiceType.query.all()
    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        item_description = request.form.get('item_description', '').strip()
        issue_description = request.form.get('issue_description', '').strip()
        service_type_id = request.form.get('service_type_id', type=int)
        category_id = request.form.get('category_id', type=int)
        if not customer_name or not item_description or not service_type_id:
            flash('Customer name, item description, and service type are required.', 'danger')
            return redirect(url_for('services.new_service'))
        service_type = ServiceType.query.get(service_type_id)
        max_charge = service_type.max_charge if service_type else 0
        service_charge = float(request.form.get('service_charge', 0))
        if current_user.role == 'worker' and max_charge > 0 and service_charge > max_charge:
            flash(f'Service charge cannot exceed KSh {max_charge:,.2f} for this service type.', 'danger')
            return redirect(url_for('services.new_service'))
        parts_cost = float(request.form.get('parts_cost', 0))
        total_cost = service_charge + parts_cost
        amount_paid = float(request.form.get('amount_paid', 0))
        balance = total_cost - amount_paid
        expected_date = request.form.get('expected_completion_date')
        expected = datetime.strptime(expected_date, '%Y-%m-%d').date() if expected_date else None
        job = ServiceJob(
            job_number=generate_job_number(),
            customer_name=customer_name,
            customer_phone=request.form.get('customer_phone', ''),
            service_type_id=service_type_id,
            service_category_id=category_id or service_type.category_id,
            item_description=item_description,
            issue_description=issue_description,
            expected_completion_date=expected,
            service_charge=service_charge,
            parts_cost=parts_cost,
            total_cost=total_cost,
            amount_paid=amount_paid,
            balance=balance,
            payment_status='paid' if balance <= 0 else ('partial' if amount_paid > 0 else 'unpaid'),
            notes=request.form.get('notes', ''),
            created_by=current_user.id
        )
        db.session.add(job)
        db.session.flush()
        if balance > 0:
            debtor = Debtor(
                source='service',
                source_id=job.id,
                customer_name=customer_name,
                customer_phone=request.form.get('customer_phone', ''),
                total_owed=total_cost,
                amount_paid=amount_paid,
                balance=balance,
                due_date=expected,
                notes=f"Service job {job.job_number}"
            )
            db.session.add(debtor)
        history = ServiceHistory(job_id=job.id, status_to='received', notes='Job created', changed_by=current_user.id)
        db.session.add(history)
        db.session.commit()
        log_activity('service_create', f"Created {job.job_number} for {customer_name}, total {total_cost:,.2f}", 'service_job', job.id)
        flash(f'Service job {job.job_number} created successfully.', 'success')
        return redirect(url_for('services.service_detail', job_id=job.id))
    return render_template('service_form.html', categories=categories, service_types=service_types)

@services_bp.route('/<int:job_id>')
@login_required
def service_detail(job_id):
    job = ServiceJob.query.get_or_404(job_id)
    history = ServiceHistory.query.filter_by(job_id=job_id).order_by(ServiceHistory.changed_at).all()
    return render_template('service_detail.html', job=job, history=history)

@services_bp.route('/<int:job_id>/status', methods=['POST'])
@login_required
def update_status(job_id):
    job = ServiceJob.query.get_or_404(job_id)
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')
    if new_status not in ['received', 'diagnosing', 'waiting_parts', 'completed', 'collected', 'cancelled']:
        flash('Invalid status', 'danger')
        return redirect(url_for('services.service_detail', job_id=job.id))
    old_status = job.status
    job.status = new_status
    job.updated_at = datetime.utcnow()
    if new_status == 'completed' and not job.completed_at:
        job.completed_at = datetime.utcnow()
    if new_status == 'collected' and not job.collected_at:
        job.collected_at = datetime.utcnow()
    history = ServiceHistory(job_id=job.id, status_from=old_status, status_to=new_status, notes=notes, changed_by=current_user.id)
    db.session.add(history)
    db.session.commit()
    log_activity('service_status', f"Job {job.job_number} status changed from {old_status} to {new_status}", 'service_job', job.id)
    flash(f'Status updated to {new_status}', 'success')
    return redirect(url_for('services.service_detail', job_id=job.id))

@services_bp.route('/<int:job_id>/payment', methods=['POST'])
@login_required
def record_payment(job_id):
    job = ServiceJob.query.get_or_404(job_id)
    amount = float(request.form.get('amount', 0))
    method = request.form.get('payment_method', 'cash')
    if amount <= 0:
        flash('Amount must be greater than 0', 'danger')
        return redirect(url_for('services.service_detail', job_id=job.id))
    if amount > job.balance:
        flash(f'Amount exceeds balance of {job.balance:,.2f}', 'danger')
        return redirect(url_for('services.service_detail', job_id=job.id))
    job.amount_paid += amount
    job.balance -= amount
    if job.balance <= 0:
        job.payment_status = 'paid'
    else:
        job.payment_status = 'partial'
    debtor = Debtor.query.filter_by(source='service', source_id=job.id).first()
    if debtor:
        debtor.amount_paid += amount
        debtor.balance -= amount
        if debtor.balance <= 0:
            debtor.status = 'paid'
        payment = Payment(debtor_id=debtor.id, amount=amount, payment_method=method, notes=f"Payment for service job {job.job_number}", user_id=current_user.id)
        db.session.add(payment)
    history = ServiceHistory(job_id=job.id, status_from=job.status, status_to=job.status, notes=f"Payment received: KSh {amount:,.2f} via {method}", changed_by=current_user.id)
    db.session.add(history)
    db.session.commit()
    log_activity('service_payment', f"Payment of {amount:,.2f} recorded for {job.job_number}, balance now {job.balance:,.2f}", 'service_job', job.id)
    flash(f'Payment of {amount:,.2f} recorded.', 'success')
    return redirect(url_for('services.service_detail', job_id=job.id))

@services_bp.route('/edit/<int:job_id>', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'admin')
def edit_service(job_id):
    job = ServiceJob.query.get_or_404(job_id)
    if request.method == 'POST':
        job.customer_name = request.form.get('customer_name', '').strip()
        job.customer_phone = request.form.get('customer_phone', '')
        job.item_description = request.form.get('item_description', '').strip()
        job.issue_description = request.form.get('issue_description', '')
        job.service_charge = float(request.form.get('service_charge', 0))
        job.parts_cost = float(request.form.get('parts_cost', 0))
        job.total_cost = job.service_charge + job.parts_cost
        job.balance = job.total_cost - job.amount_paid
        expected = request.form.get('expected_completion_date')
        job.expected_completion_date = datetime.strptime(expected, '%Y-%m-%d').date() if expected else None
        job.notes = request.form.get('notes', '')
        job.technician_notes = request.form.get('technician_notes', '')
        job.updated_at = datetime.utcnow()
        debtor = Debtor.query.filter_by(source='service', source_id=job.id).first()
        if debtor:
            debtor.total_owed = job.total_cost
            debtor.balance = job.balance
            debtor.due_date = job.expected_completion_date
        db.session.commit()
        log_activity('service_edit', f"Edited job {job.job_number}", 'service_job', job.id)
        flash('Service job updated.', 'success')
        return redirect(url_for('services.service_detail', job_id=job.id))
    categories = ServiceCategory.query.all()
    service_types = ServiceType.query.all()
    return render_template('service_form.html', job=job, categories=categories, service_types=service_types)

@services_bp.route('/ready')
@login_required
def ready_for_collection():
    jobs = ServiceJob.query.filter_by(status='completed', collected_at=None).order_by(ServiceJob.completed_at).all()
    return render_template('services_ready.html', jobs=jobs)

@services_bp.route('/overdue')
@login_required
@role_required('owner', 'admin')
def overdue():
    today = date.today()
    jobs = ServiceJob.query.filter(ServiceJob.expected_completion_date < today, ServiceJob.status.notin_(['collected', 'cancelled'])).order_by(ServiceJob.expected_completion_date).all()
    return render_template('services_overdue.html', jobs=jobs)

@services_bp.route('/categories', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'admin')
def manage_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_category':
            name = request.form.get('name')
            if name:
                cat = ServiceCategory(name=name)
                db.session.add(cat)
                db.session.commit()
                log_activity('service_category_create', f"Added category {name}", 'service_category', cat.id)
                flash(f'Category "{name}" added.', 'success')
        elif action == 'add_type':
            cat_id = request.form.get('category_id', type=int)
            name = request.form.get('name')
            max_charge = float(request.form.get('max_charge', 0))
            if cat_id and name:
                st = ServiceType(category_id=cat_id, name=name, max_charge=max_charge)
                db.session.add(st)
                db.session.commit()
                log_activity('service_type_create', f"Added type {name} with max charge {max_charge}", 'service_type', st.id)
                flash(f'Service type "{name}" added.', 'success')
        elif action == 'edit_type':
            type_id = request.form.get('type_id', type=int)
            max_charge = float(request.form.get('max_charge', 0))
            st = ServiceType.query.get(type_id)
            if st:
                old = st.max_charge
                st.max_charge = max_charge
                db.session.commit()
                log_activity('service_type_edit', f"Changed max charge for {st.name} from {old} to {max_charge}", 'service_type', st.id)
                flash('Max charge updated.', 'success')
        elif action == 'delete_type':
            type_id = request.form.get('type_id', type=int)
            st = ServiceType.query.get(type_id)
            if st and not st.jobs:
                db.session.delete(st)
                db.session.commit()
                log_activity('service_type_delete', f"Deleted type {st.name}", 'service_type', type_id)
                flash('Service type deleted.', 'success')
            else:
                flash('Cannot delete type with existing jobs.', 'danger')
        return redirect(url_for('services.manage_categories'))
    categories = ServiceCategory.query.all()
    service_types = ServiceType.query.all()
    return render_template('service_categories.html', categories=categories, service_types=service_types)
