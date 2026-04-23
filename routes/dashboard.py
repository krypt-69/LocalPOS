"""
Dashboard routes - Main overview page with analytics
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from database.models import db, Sale, SaleItem, Product, Category, Debtor
from datetime import datetime, timedelta, date
from sqlalchemy import func, extract

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def dashboard_home():
    """Main dashboard page"""
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    # Today's sales
    today_sales = db.session.query(func.sum(Sale.final_amount)).filter(
        func.date(Sale.sale_date) == today
    ).scalar() or 0
    
    today_transactions = Sale.query.filter(
        func.date(Sale.sale_date) == today
    ).count()
    
    # Today's profit
    today_items = SaleItem.query.join(Sale).filter(
        func.date(Sale.sale_date) == today
    ).all()
    
    today_profit = 0
    for item in today_items:
        product = Product.query.get(item.product_id)
        if product:
            today_profit += item.quantity * (item.price_at_sale - product.buying_price)
    
    # Payment breakdown today
    cash_today = db.session.query(func.sum(Sale.final_amount)).filter(
        func.date(Sale.sale_date) == today,
        Sale.payment_method == 'cash'
    ).scalar() or 0
    
    mpesa_today = db.session.query(func.sum(Sale.final_amount)).filter(
        func.date(Sale.sale_date) == today,
        Sale.payment_method == 'mpesa'
    ).scalar() or 0
    
    credit_today = db.session.query(func.sum(Sale.final_amount)).filter(
        func.date(Sale.sale_date) == today,
        Sale.payment_method == 'credit'
    ).scalar() or 0
    
    # Low stock count
    low_stock_count = Product.query.filter(
        Product.current_stock <= Product.reorder_level,
        Product.is_active == True
    ).count()
    
    # Critical stock (out of stock)
    critical_count = Product.query.filter(
        Product.current_stock == 0,
        Product.is_active == True
    ).count()
    
    # Total debt outstanding
    total_debt = db.session.query(func.sum(Debtor.balance)).scalar() or 0
    
    # Overdue debts
    overdue_debts = Debtor.query.filter(
        Debtor.due_date < date.today(),
        Debtor.balance > 0
    ).count()
    
    # Top 5 products this week
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_quantity')
    ).join(SaleItem.product)\
     .join(SaleItem.sale)\
     .filter(func.date(Sale.sale_date) >= start_of_week)\
     .group_by(Product.id)\
     .order_by(func.sum(SaleItem.quantity).desc())\
     .limit(5)\
     .all()
    
    # Recent sales (last 5)
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         today_sales=today_sales,
                         today_transactions=today_transactions,
                         today_profit=today_profit,
                         cash_today=cash_today,
                         mpesa_today=mpesa_today,
                         credit_today=credit_today,
                         low_stock_count=low_stock_count,
                         critical_count=critical_count,
                         total_debt=total_debt,
                         overdue_debts=overdue_debts,
                         top_products=top_products,
                         recent_sales=recent_sales)

@dashboard_bp.route('/api/sales-trend')
@login_required
def sales_trend():
    """API endpoint for sales trend chart (last 7 days)"""
    today = date.today()
    trend_data = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        daily_sales = db.session.query(func.sum(Sale.final_amount)).filter(
            func.date(Sale.sale_date) == day
        ).scalar() or 0
        
        trend_data.append({
            'date': day.strftime('%Y-%m-%d'),
            'sales': float(daily_sales)
        })
    
    return jsonify(trend_data)

@dashboard_bp.route('/api/category-sales')
@login_required
def category_sales():
    """API endpoint for category sales breakdown (current month)"""
    start_of_month = date.today().replace(day=1)
    
    category_data = db.session.query(
        Category.name,
        func.sum(SaleItem.quantity * SaleItem.price_at_sale).label('total')
    ).join(Product, Product.category_id == Category.id)\
     .join(SaleItem, SaleItem.product_id == Product.id)\
     .join(Sale, Sale.id == SaleItem.sale_id)\
     .filter(func.date(Sale.sale_date) >= start_of_month)\
     .group_by(Category.id)\
     .all()
    
    return jsonify([{
        'category': cat_name,
        'total': float(total)
    } for cat_name, total in category_data])

@dashboard_bp.route('/api/daily-summary')
@login_required
def daily_summary():
    """API endpoint for daily closing summary"""
    today = date.today()
    
    total_sales = db.session.query(func.sum(Sale.final_amount)).filter(
        func.date(Sale.sale_date) == today
    ).scalar() or 0
    
    transaction_count = Sale.query.filter(
        func.date(Sale.sale_date) == today
    ).count()
    
    # Calculate profit
    today_items = SaleItem.query.join(Sale).filter(
        func.date(Sale.sale_date) == today
    ).all()
    
    total_profit = 0
    for item in today_items:
        product = Product.query.get(item.product_id)
        if product:
            total_profit += item.quantity * (item.price_at_sale - product.buying_price)
    
    # Best selling product today
    best_product = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_qty')
    ).join(SaleItem.product)\
     .join(SaleItem.sale)\
     .filter(func.date(Sale.sale_date) == today)\
     .group_by(Product.id)\
     .order_by(func.sum(SaleItem.quantity).desc())\
     .first()
    
    return jsonify({
        'total_sales': float(total_sales),
        'transaction_count': transaction_count,
        'total_profit': float(total_profit),
        'best_product': best_product[0] if best_product else 'None',
        'best_product_quantity': int(best_product[1]) if best_product else 0
    })
