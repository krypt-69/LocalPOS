"""
Stock Management routes - View stock, low stock alerts, stock adjustments
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.models import db, Product, Category, StockEntry, SaleItem, Sale
from datetime import datetime, timedelta
from sqlalchemy import func

stock_bp = Blueprint('stock_management', __name__, url_prefix='/stock')

def calculate_days_remaining(product):
    """Calculate estimated days until stock runs out"""
    if product.current_stock <= 0:
        return 0
    
    # Get average daily sales for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Fixed: Use Sale.sale_date instead of just sale_date
    avg_daily_sales = db.session.query(
        func.coalesce(func.sum(SaleItem.quantity) / 30.0, 0)
    ).filter(
        SaleItem.product_id == product.id,
        SaleItem.sale.has(Sale.sale_date >= thirty_days_ago)
    ).scalar()
    
    if avg_daily_sales <= 0:
        return 999  # No sales, unlimited days
    
    days = int(product.current_stock / avg_daily_sales)
    return days

def get_stock_status(product):
    """Get stock status with color coding"""
    if product.current_stock <= 0:
        return {'status': 'out_of_stock', 'color': 'danger', 'text': 'Out of Stock'}
    elif product.current_stock <= product.reorder_level:
        return {'status': 'critical', 'color': 'danger', 'text': 'Critical'}
    elif product.current_stock <= product.reorder_level * 2:
        return {'status': 'low', 'color': 'warning', 'text': 'Low'}
    else:
        return {'status': 'healthy', 'color': 'success', 'text': 'Healthy'}

@stock_bp.route('/')
@login_required
def stock_list():
    """View all products with stock levels"""
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    
    query = Product.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.order_by(Product.name).all()
    categories = Category.query.all()
    
    # Add stock status to each product
    for product in products:
        product.stock_status = get_stock_status(product)
        product.days_remaining = calculate_days_remaining(product)
    
    return render_template('stock_list.html', 
                         products=products, 
                         categories=categories,
                         selected_category=category_id,
                         search=search)

@stock_bp.route('/low-stock')
@login_required
def low_stock():
    """Low stock alerts page"""
    # Get products below reorder level
    products = Product.query.filter(
        Product.current_stock <= Product.reorder_level,
        Product.is_active == True
    ).order_by(Product.current_stock).all()
    
    categories = Category.query.all()
    
    # Add calculated fields
    for product in products:
        product.stock_status = get_stock_status(product)
        product.days_remaining = calculate_days_remaining(product)
        product.suggested_restock = product.reorder_level * 2  # Simple suggestion
    
    # Summary statistics
    critical_count = sum(1 for p in products if p.current_stock <= 0)
    low_count = len(products) - critical_count
    
    return render_template('low_stock.html',
                         products=products,
                         categories=categories,
                         critical_count=critical_count,
                         low_count=low_count)

@stock_bp.route('/dead-stock')
@login_required
def dead_stock():
    """Products not sold in last 30 days"""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Find products with no sales in last 30 days
    products = Product.query.filter(
        Product.is_active == True,
        Product.current_stock > 0
    ).all()
    
    dead_products = []
    for product in products:
        # Fixed: Use Sale.sale_date in the query
        last_sale = db.session.query(SaleItem)\
            .filter(SaleItem.product_id == product.id)\
            .join(SaleItem.sale)\
            .filter(Sale.sale_date >= thirty_days_ago)\
            .first()
        
        if not last_sale:
            product.days_unsold = 30
            dead_products.append(product)
    
    return render_template('dead_stock.html', products=dead_products)

@stock_bp.route('/adjust/<int:product_id>', methods=['GET', 'POST'])
@login_required
def adjust_stock(product_id):
    """Manual stock adjustment for damaged/lost items"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        adjustment_type = request.form.get('adjustment_type')  # add or remove
        quantity = int(request.form.get('quantity', 0))
        reason = request.form.get('reason', '')
        
        if quantity <= 0:
            flash('Quantity must be greater than 0', 'danger')
            return redirect(url_for('stock_management.adjust_stock', product_id=product_id))
        
        try:
            if adjustment_type == 'remove':
                if quantity > product.current_stock:
                    flash(f'Cannot remove {quantity} items. Only {product.current_stock} in stock.', 'danger')
                    return redirect(url_for('stock_management.adjust_stock', product_id=product_id))
                
                product.current_stock -= quantity
                adjustment_note = f"REMOVED: {quantity} items. Reason: {reason}"
                flash(f'✅ Removed {quantity} items from {product.name}', 'success')
                
            else:  # add
                product.current_stock += quantity
                adjustment_note = f"ADDED: {quantity} items. Reason: {reason}"
                flash(f'✅ Added {quantity} items to {product.name}', 'success')
            
            # Record adjustment as a stock entry (negative quantity for removal)
            stock_entry = StockEntry(
                product_id=product.id,
                quantity=-quantity if adjustment_type == 'remove' else quantity,
                buying_price=product.buying_price,
                selling_price=product.selling_price,
                supplier='MANUAL_ADJUSTMENT',
                notes=adjustment_note,
                user_id=current_user.id
            )
            db.session.add(stock_entry)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adjusting stock: {str(e)}', 'danger')
        
        return redirect(url_for('stock_management.stock_list'))
    
    return render_template('adjust_stock.html', product=product)

@stock_bp.route('/update-reorder/<int:product_id>', methods=['POST'])
@login_required
def update_reorder_level(product_id):
    """Update reorder level for a product"""
    product = Product.query.get_or_404(product_id)
    new_level = int(request.form.get('reorder_level', 5))
    
    if new_level < 0:
        flash('Reorder level cannot be negative', 'danger')
    else:
        product.reorder_level = new_level
        db.session.commit()
        flash(f'Reorder level for {product.name} updated to {new_level}', 'success')
    
    return redirect(url_for('stock_management.stock_list'))

@stock_bp.route('/api/low-stock-count')
@login_required
def low_stock_count():
    """API endpoint for low stock count (for dashboard)"""
    count = Product.query.filter(
        Product.current_stock <= Product.reorder_level,
        Product.is_active == True
    ).count()
    
    return jsonify({'low_stock_count': count})

@stock_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    """View detailed product information"""
    product = Product.query.get_or_404(product_id)
    
    # Get stock history (last 10 entries)
    stock_history = StockEntry.query.filter_by(product_id=product_id)\
        .order_by(StockEntry.entry_date.desc())\
        .limit(10)\
        .all()
    
    # Get recent sales
    recent_sales = SaleItem.query.filter_by(product_id=product_id)\
        .join(SaleItem.sale)\
        .order_by(Sale.sale_date.desc())\
        .limit(10)\
        .all()
    
    product.stock_status = get_stock_status(product)
    product.days_remaining = calculate_days_remaining(product)
    
    return render_template('product_detail.html',
                         product=product,
                         stock_history=stock_history,
                         recent_sales=recent_sales)

@stock_bp.route('/mark-inactive/<int:product_id>', methods=['POST'])
@login_required
def mark_inactive(product_id):
    """Mark product as inactive (soft delete)"""
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    flash(f'{product.name} has been marked as inactive', 'success')
    return jsonify({'success': True})
