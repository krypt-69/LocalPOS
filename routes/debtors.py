"""
Debtors routes - Credit management and payment tracking
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.models import db, Debtor, Payment, Sale, SaleItem
from datetime import datetime, timedelta, date
from sqlalchemy import func

debtors_bp = Blueprint('debtors', __name__, url_prefix='/debtors')

def get_debt_status(balance, due_date=None):
    """Get debt status based on balance and due date"""
    if balance <= 0:
        return {'status': 'paid', 'color': 'success', 'text': 'Paid'}
    
    if due_date:
        today = date.today()
        if due_date < today:
            return {'status': 'overdue', 'color': 'danger', 'text': 'Overdue'}
        elif due_date <= today + timedelta(days=3):
            return {'status': 'due_soon', 'color': 'warning', 'text': 'Due Soon'}
    
    return {'status': 'pending', 'color': 'info', 'text': 'Pending'}

def get_aging_category(created_date):
    """Categorize debt by age"""
    days_old = (date.today() - created_date).days
    
    if days_old <= 3:
        return '0-3 days'
    elif days_old <= 14:
        return '4-14 days'
    else:
        return '15+ days'

@debtors_bp.route('/')
@login_required
def debtors_list():
    """List all debtors with filtering"""
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Debtor.query.filter(Debtor.balance > 0)
    
    if status_filter == 'overdue':
        query = query.filter(Debtor.due_date < date.today(), Debtor.balance > 0)
    elif status_filter == 'due_soon':
        query = query.filter(Debtor.due_date <= date.today() + timedelta(days=3), 
                            Debtor.due_date >= date.today(),
                            Debtor.balance > 0)
    elif status_filter == 'pending':
        query = query.filter(Debtor.due_date >= date.today(), Debtor.balance > 0)
    
    if search:
        query = query.filter(
            db.or_(
                Debtor.customer_name.ilike(f'%{search}%'),
                Debtor.customer_phone.ilike(f'%{search}%')
            )
        )
    
    debtors = query.order_by(Debtor.balance.desc()).all()
    
    # Add status to each debtor
    for debtor in debtors:
        debtor.status_info = get_debt_status(debtor.balance, debtor.due_date)
        debtor.aging_category = get_aging_category(debtor.created_at.date())
    
    # Summary statistics
    total_debt = db.session.query(func.sum(Debtor.balance)).scalar() or 0
    total_debtors = Debtor.query.filter(Debtor.balance > 0).count()
    overdue_count = Debtor.query.filter(
        Debtor.due_date < date.today(), 
        Debtor.balance > 0
    ).count()
    
    return render_template('debtors_list.html',
                         debtors=debtors,
                         total_debt=total_debt,
                         total_debtors=total_debtors,
                         overdue_count=overdue_count,
                         status_filter=status_filter,
                         search=search,
                         today=date.today())  # Added today

@debtors_bp.route('/<int:debtor_id>')
@login_required
def debtor_profile(debtor_id):
    """View detailed debtor profile"""
    debtor = Debtor.query.get_or_404(debtor_id)
    
    # Get payment history
    payments = Payment.query.filter_by(debtor_id=debtor_id)\
        .order_by(Payment.payment_date.desc())\
        .all()
    
    # Get sale details
    sale = Sale.query.get(debtor.sale_id)
    sale_items = SaleItem.query.filter_by(sale_id=sale.id).all() if sale else []
    
    debtor.status_info = get_debt_status(debtor.balance, debtor.due_date)
    
    return render_template('debtor_profile.html',
                         debtor=debtor,
                         payments=payments,
                         sale=sale,
                         sale_items=sale_items,
                         today=date.today())  # Added today

@debtors_bp.route('/add-payment/<int:debtor_id>', methods=['POST'])
@login_required
def add_payment(debtor_id):
    """Record a payment against a debt"""
    debtor = Debtor.query.get_or_404(debtor_id)
    amount = float(request.form.get('amount', 0))
    payment_method = request.form.get('payment_method', 'cash')
    notes = request.form.get('notes', '')
    
    if amount <= 0:
        flash('Payment amount must be greater than 0', 'danger')
        return redirect(url_for('debtors.debtor_profile', debtor_id=debtor_id))
    
    if amount > debtor.balance:
        flash(f'Payment amount (KSh {amount}) exceeds balance (KSh {debtor.balance})', 'danger')
        return redirect(url_for('debtors.debtor_profile', debtor_id=debtor_id))
    
    try:
        # Record payment
        payment = Payment(
            debtor_id=debtor.id,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            user_id=current_user.id
        )
        db.session.add(payment)
        
        # Update debtor balance
        debtor.amount_paid += amount
        debtor.balance -= amount
        debtor.updated_at = datetime.utcnow()
        
        # Update status if fully paid
        if debtor.balance <= 0:
            debtor.status = 'paid'
        
        # Update sale balance
        sale = Sale.query.get(debtor.sale_id)
        if sale:
            sale.amount_paid += amount
            sale.balance = debtor.balance
        
        db.session.commit()
        
        flash(f'✅ Payment of KSh {amount:,.2f} recorded successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording payment: {str(e)}', 'danger')
    
    return redirect(url_for('debtors.debtor_profile', debtor_id=debtor_id))

@debtors_bp.route('/write-off/<int:debtor_id>', methods=['POST'])
@login_required
def write_off_debt(debtor_id):
    """Write off uncollectible debt"""
    debtor = Debtor.query.get_or_404(debtor_id)
    
    if debtor.balance <= 0:
        flash('Debt is already fully paid', 'warning')
        return redirect(url_for('debtors.debtor_profile', debtor_id=debtor_id))
    
    reason = request.form.get('reason', '')
    
    try:
        # Record write-off as a special payment
        payment = Payment(
            debtor_id=debtor.id,
            amount=debtor.balance,
            payment_method='write_off',
            notes=f"WRITE OFF - Reason: {reason}",
            user_id=current_user.id
        )
        db.session.add(payment)
        
        # Update debtor
        debtor.amount_paid += debtor.balance
        debtor.balance = 0
        debtor.status = 'written_off'
        debtor.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'✅ Debt of KSh {debtor.amount_paid:,.2f} written off', 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error writing off debt: {str(e)}', 'danger')
    
    return redirect(url_for('debtors.debtors_list'))

@debtors_bp.route('/statement/<int:debtor_id>')
@login_required
def statement(debtor_id):
    """Generate customer statement"""
    debtor = Debtor.query.get_or_404(debtor_id)
    
    payments = Payment.query.filter_by(debtor_id=debtor_id)\
        .order_by(Payment.payment_date)\
        .all()
    
    sale = Sale.query.get(debtor.sale_id)
    sale_items = SaleItem.query.filter_by(sale_id=sale.id).all() if sale else []
    
    return render_template('debtor_statement.html',
                         debtor=debtor,
                         payments=payments,
                         sale=sale,
                         sale_items=sale_items,
                         now=datetime.now())

@debtors_bp.route('/api/summary')
@login_required
def api_summary():
    """API endpoint for dashboard summary"""
    total_debt = db.session.query(func.sum(Debtor.balance)).scalar() or 0
    overdue_count = Debtor.query.filter(
        Debtor.due_date < date.today(), 
        Debtor.balance > 0
    ).count()
    
    return jsonify({
        'total_debt': total_debt,
        'overdue_count': overdue_count,
        'debtor_count': Debtor.query.filter(Debtor.balance > 0).count()
    })
