"""
Reports routes - Analytics and data exports
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, Response
from flask_login import login_required, current_user
from database.models import db, Sale, SaleItem, Product, Category, User, Debtor
from datetime import datetime, timedelta, date
from sqlalchemy import func
import pandas as pd
import io
from io import BytesIO
import csv

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def reports_page():
    """Advanced reports page"""
    return render_template('reports.html', now=datetime.now())

@reports_bp.route('/sales')
@login_required
def sales_report():
    """Generate sales report with filters"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('type', 'sales')
    
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    if report_type == 'sales':
        # Sales report
        sales = Sale.query.filter(
            Sale.sale_date >= start,
            Sale.sale_date <= end
        ).order_by(Sale.sale_date.desc()).all()
        
        total_sales = sum(s.final_amount for s in sales)
        total_transactions = len(sales)
        total_profit = 0
        
        # Calculate profit for each sale
        for sale in sales:
            for item in sale.items:
                product = Product.query.get(item.product_id)
                if product:
                    total_profit += item.quantity * (item.price_at_sale - product.buying_price)
        
        cash_total = sum(s.final_amount for s in sales if s.payment_method == 'cash')
        mpesa_total = sum(s.final_amount for s in sales if s.payment_method == 'mpesa')
        credit_total = sum(s.final_amount for s in sales if s.payment_method == 'credit')
        
        return render_template('sales_report.html',
                             sales=sales,
                             start_date=start_date,
                             end_date=end_date,
                             total_sales=total_sales,
                             total_transactions=total_transactions,
                             total_profit=total_profit,
                             cash_total=cash_total,
                             mpesa_total=mpesa_total,
                             credit_total=credit_total,
                             now=datetime.now())
    
    elif report_type == 'products':
        # Products performance report
        products = db.session.query(
            Product.name,
            Category.name.label('category'),
            func.sum(SaleItem.quantity).label('total_sold'),
            func.sum(SaleItem.quantity * SaleItem.price_at_sale).label('total_revenue'),
            Product.current_stock,
            Product.buying_price,
            Product.selling_price
        ).join(Category, Category.id == Product.category_id)\
         .outerjoin(SaleItem, SaleItem.product_id == Product.id)\
         .outerjoin(Sale, Sale.id == SaleItem.sale_id)\
         .filter(
             (Sale.sale_date >= start) | (Sale.sale_date == None),
             (Sale.sale_date <= end) | (Sale.sale_date == None)
         )\
         .group_by(Product.id)\
         .order_by(func.sum(SaleItem.quantity).desc())\
         .all()
        
        return render_template('products_report.html',
                             products=products,
                             start_date=start_date,
                             end_date=end_date,
                             now=datetime.now())
    
    elif report_type == 'categories':
        # Category performance
        categories = db.session.query(
            Category.name,
            func.count(Sale.id).label('transaction_count'),
            func.sum(SaleItem.quantity).label('items_sold'),
            func.sum(SaleItem.quantity * SaleItem.price_at_sale).label('revenue')
        ).join(Product, Product.category_id == Category.id)\
         .join(SaleItem, SaleItem.product_id == Product.id)\
         .join(Sale, Sale.id == SaleItem.sale_id)\
         .filter(Sale.sale_date >= start, Sale.sale_date <= end)\
         .group_by(Category.id)\
         .all()
        
        total_revenue = sum(c.revenue for c in categories) if categories else 0
        
        return render_template('categories_report.html',
                             categories=categories,
                             total_revenue=total_revenue,
                             start_date=start_date,
                             end_date=end_date,
                             now=datetime.now())
    
    elif report_type == 'users':
        # User performance
        users = db.session.query(
            User.username,
            User.full_name,
            func.count(Sale.id).label('sales_count'),
            func.sum(Sale.final_amount).label('total_sales'),
            func.avg(Sale.final_amount).label('avg_sale')
        ).join(Sale, Sale.user_id == User.id)\
         .filter(Sale.sale_date >= start, Sale.sale_date <= end)\
         .group_by(User.id)\
         .order_by(func.sum(Sale.final_amount).desc())\
         .all()
        
        return render_template('users_report.html',
                             users=users,
                             start_date=start_date,
                             end_date=end_date,
                             now=datetime.now())
    
    return redirect(url_for('reports.reports_page'))

@reports_bp.route('/daily-closing')
@login_required
def daily_closing():
    """Daily closing report"""
    closing_date = request.args.get('date', date.today().isoformat())
    closing_date_obj = datetime.strptime(closing_date, '%Y-%m-%d').date()
    
    # Sales for the day
    sales = Sale.query.filter(
        func.date(Sale.sale_date) == closing_date_obj
    ).all()
    
    total_sales = sum(s.final_amount for s in sales)
    total_transactions = len(sales)
    
    # Calculate profit
    total_profit = 0
    for sale in sales:
        for item in sale.items:
            product = Product.query.get(item.product_id)
            if product:
                total_profit += item.quantity * (item.price_at_sale - product.buying_price)
    
    # Payment breakdown
    cash_total = sum(s.final_amount for s in sales if s.payment_method == 'cash')
    mpesa_total = sum(s.final_amount for s in sales if s.payment_method == 'mpesa')
    credit_total = sum(s.final_amount for s in sales if s.payment_method == 'credit')
    
    # Best selling product
    best_product = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_qty')
    ).join(SaleItem.product)\
     .join(SaleItem.sale)\
     .filter(func.date(Sale.sale_date) == closing_date_obj)\
     .group_by(Product.id)\
     .order_by(func.sum(SaleItem.quantity).desc())\
     .first()
    
    return render_template('daily_closing.html',
                         closing_date=closing_date,
                         total_sales=total_sales,
                         total_transactions=total_transactions,
                         total_profit=total_profit,
                         cash_total=cash_total,
                         mpesa_total=mpesa_total,
                         credit_total=credit_total,
                         best_product=best_product,
                         sales=sales,
                         now=datetime.now())

@reports_bp.route('/export/csv')
@login_required
def export_csv():
    """Export sales data to CSV"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    sales = Sale.query.filter(
        Sale.sale_date >= start,
        Sale.sale_date <= end
    ).order_by(Sale.sale_date.desc()).all()
    
    # Prepare data for CSV
    data = []
    for sale in sales:
        for item in sale.items:
            product = Product.query.get(item.product_id)
            data.append({
                'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'Receipt #': sale.receipt_number,
                'Product': item.product.name,
                'Quantity': item.quantity,
                'Price': item.price_at_sale,
                'Total': item.total,
                'Payment Method': sale.payment_method.upper(),
                'Customer': sale.customer_name or 'Walk-in',
                'Cashier': sale.user.username
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=sales_report_{start_date}_to_{end_date}.csv'}
    )

@reports_bp.route('/export/excel')
@login_required
def export_excel():
    """Export sales data to Excel"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    sales = Sale.query.filter(
        Sale.sale_date >= start,
        Sale.sale_date <= end
    ).order_by(Sale.sale_date.desc()).all()
    
    # Prepare data
    data = []
    for sale in sales:
        for item in sale.items:
            data.append({
                'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'Receipt #': sale.receipt_number,
                'Product': item.product.name,
                'Quantity': item.quantity,
                'Price': item.price_at_sale,
                'Total': item.total,
                'Payment Method': sale.payment_method.upper(),
                'Customer': sale.customer_name or 'Walk-in',
                'Cashier': sale.user.username
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sales Report', index=False)
        
        # Add summary sheet
        summary = pd.DataFrame({
            'Metric': ['Total Sales', 'Total Transactions', 'Average Sale', 'Report Period'],
            'Value': [
                f"KSh {sum(s.final_amount for s in sales):,.2f}",
                len(sales),
                f"KSh {(sum(s.final_amount for s in sales) / len(sales) if sales else 0):,.2f}",
                f"{start_date} to {end_date}"
            ]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'sales_report_{start_date}_to_{end_date}.xlsx'
    )
