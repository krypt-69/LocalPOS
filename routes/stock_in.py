"""
Stock In routes - Add new stock, batch entry, CSV import
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.models import db, Product, Category, StockEntry
from utils.validators import validate_stock_entry
from utils.helpers import calculate_profit, validate_prices, format_currency
from utils.csv_excel_handler import import_products_from_file, allowed_file, preview_import_file
from werkzeug.utils import secure_filename
import os
from datetime import datetime

stock_in_bp = Blueprint('stock_in', __name__, url_prefix='/stock-in')

@stock_in_bp.route('/')
@login_required
def stock_in_page():
    """Stock In main page - single entry form"""
    categories = Category.query.filter_by().all()
    return render_template('stock_in.html', categories=categories, format_currency=format_currency)

@stock_in_bp.route('/add', methods=['POST'])
@login_required
def add_stock():
    """Add single stock entry"""
    product_name = request.form.get('product_name', '').strip()
    category_id = request.form.get('category_id')
    quantity = request.form.get('quantity')
    buying_price = request.form.get('buying_price')
    selling_price = request.form.get('selling_price')
    supplier = request.form.get('supplier', '')
    notes = request.form.get('notes', '')
    
    # Validate
    validation = validate_stock_entry(product_name, quantity, buying_price, selling_price)
    if not validation['valid']:
        for error in validation['errors']:
            flash(error, 'danger')
        return redirect(url_for('stock_in.stock_in_page'))
    
    quantity = int(quantity)
    buying_price = float(buying_price)
    selling_price = float(selling_price)
    
    # Price validation warning
    price_check = validate_prices(buying_price, selling_price)
    if not price_check['valid']:
        flash(price_check['warning'], 'warning')
    
    try:
        # Check if product exists
        product = Product.query.filter_by(name=product_name).first()
        
        if product:
            # Update existing product
            product.current_stock += quantity
            product.buying_price = buying_price
            product.selling_price = selling_price
            product.updated_at = datetime.utcnow()
            db.session.flush()
            flash(f'Updated existing product: {product_name}. New stock: {product.current_stock}', 'success')
        else:
            # Create new product
            product = Product(
                name=product_name,
                category_id=int(category_id),
                current_stock=quantity,
                buying_price=buying_price,
                selling_price=selling_price
            )
            db.session.add(product)
            db.session.flush()  # This assigns an ID to product
            flash(f'Created new product: {product_name}', 'success')
        
        # Now product.id is guaranteed to exist
        if not product.id:
            raise Exception("Product ID not generated")
        
        # Record stock entry
        stock_entry = StockEntry(
            product_id=product.id,
            quantity=quantity,
            buying_price=buying_price,
            selling_price=selling_price,
            supplier=supplier,
            notes=notes,
            user_id=current_user.id
        )
        db.session.add(stock_entry)
        db.session.commit()
        
        # Calculate profit for feedback
        profit = calculate_profit(buying_price, selling_price, quantity)
        flash(f'✅ Stock added! Profit potential: {format_currency(profit["total"])}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding stock: {str(e)}', 'danger')
        return redirect(url_for('stock_in.stock_in_page'))
    
    return redirect(url_for('stock_in.stock_in_page'))

@stock_in_bp.route('/search-product')
@login_required
def search_product():
    """AJAX endpoint for product suggestions"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    products = Product.query.filter(Product.name.ilike(f'%{query}%')).limit(10).all()
    
    results = [{
        'id': p.id,
        'name': p.name,
        'buying_price': p.buying_price,
        'selling_price': p.selling_price,
        'category_id': p.category_id,
        'current_stock': p.current_stock
    } for p in products]
    
    return jsonify(results)

@stock_in_bp.route('/get-product/<int:product_id>')
@login_required
def get_product(product_id):
    """Get product details for quick restock"""
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'buying_price': product.buying_price,
        'selling_price': product.selling_price,
        'category_id': product.category_id,
        'supplier': product.supplier
    })

@stock_in_bp.route('/batch')
@login_required
def batch_entry():
    """Batch entry page - table-based multiple items"""
    categories = Category.query.all()
    return render_template('stock_in_batch.html', categories=categories)

@stock_in_bp.route('/batch/add', methods=['POST'])
@login_required
def add_batch_stock():
    """Add multiple stock entries at once"""
    products_data = request.form.get('products_data')
    import json
    
    try:
        products = json.loads(products_data)
        added_count = 0
        
        for item in products:
            product_name = item.get('name', '').strip()
            category_id = item.get('category_id')
            quantity = int(item.get('quantity', 0))
            buying_price = float(item.get('buying_price', 0))
            selling_price = float(item.get('selling_price', 0))
            supplier = item.get('supplier', '')
            
            if quantity <= 0 or buying_price <= 0:
                continue
            
            # Check if product exists
            product = Product.query.filter_by(name=product_name).first()
            
            if product:
                product.current_stock += quantity
                product.buying_price = buying_price
                product.selling_price = selling_price
                db.session.flush()
            else:
                product = Product(
                    name=product_name,
                    category_id=int(category_id),
                    current_stock=quantity,
                    buying_price=buying_price,
                    selling_price=selling_price
                )
                db.session.add(product)
                db.session.flush()
            
            # Record stock entry
            stock_entry = StockEntry(
                product_id=product.id,
                quantity=quantity,
                buying_price=buying_price,
                selling_price=selling_price,
                supplier=supplier,
                user_id=current_user.id
            )
            db.session.add(stock_entry)
            added_count += 1
        
        db.session.commit()
        flash(f'✅ Successfully added {added_count} products!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding batch: {str(e)}', 'danger')
    
    return redirect(url_for('stock_in.batch_entry'))

@stock_in_bp.route('/import')
@login_required
def import_page():
    """CSV/Excel import page"""
    return render_template('stock_in_import.html')

@stock_in_bp.route('/import/preview', methods=['POST'])
@login_required
def preview_import():
    """Preview CSV/Excel file before import"""
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('stock_in.import_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('stock_in.import_page'))
    
    if not allowed_file(file.filename):
        flash('File type not allowed. Use CSV or Excel files.', 'danger')
        return redirect(url_for('stock_in.import_page'))
    
    preview_data, error = preview_import_file(file)
    
    if error:
        flash(error, 'danger')
        return redirect(url_for('stock_in.import_page'))
    
    # Store file temporarily for actual import
    filename = secure_filename(file.filename)
    temp_path = os.path.join('/tmp', filename)
    file.save(temp_path)
    
    return render_template('stock_in_import.html', 
                         preview=preview_data, 
                         temp_file=temp_path,
                         filename=filename)

@stock_in_bp.route('/import/confirm', methods=['POST'])
@login_required
def confirm_import():
    """Confirm and process the imported file"""
    temp_file = request.form.get('temp_file')
    file_type = request.form.get('file_type', 'csv')
    
    if not temp_file or not os.path.exists(temp_file):
        flash('Import file not found', 'danger')
        return redirect(url_for('stock_in.import_page'))
    
    result = import_products_from_file(temp_file, file_type)
    
    if not result['success']:
        flash(f'Import failed: {result["error"]}', 'danger')
        return redirect(url_for('stock_in.import_page'))
    
    added_count = 0
    for product_data in result['products']:
        try:
            product_name = product_data.get('name', '').strip()
            category_name = product_data.get('category', '').strip()
            quantity = int(product_data.get('quantity', 0))
            buying_price = float(product_data.get('buying_price', 0))
            selling_price = float(product_data.get('selling_price', 0))
            supplier = product_data.get('supplier', '')
            
            if quantity <= 0 or buying_price <= 0:
                continue
            
            # Find or create category
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.flush()
            
            # Find or create product
            product = Product.query.filter_by(name=product_name).first()
            if product:
                product.current_stock += quantity
                product.buying_price = buying_price
                product.selling_price = selling_price
                db.session.flush()
            else:
                product = Product(
                    name=product_name,
                    category_id=category.id,
                    current_stock=quantity,
                    buying_price=buying_price,
                    selling_price=selling_price
                )
                db.session.add(product)
                db.session.flush()
            
            # Record stock entry
            stock_entry = StockEntry(
                product_id=product.id,
                quantity=quantity,
                buying_price=buying_price,
                selling_price=selling_price,
                supplier=supplier,
                user_id=current_user.id
            )
            db.session.add(stock_entry)
            added_count += 1
            
        except Exception as e:
            flash(f'Error importing {product_data.get("name", "unknown")}: {str(e)}', 'warning')
            continue
    
    db.session.commit()
    
    # Clean up temp file
    os.remove(temp_file)
    
    flash(f'✅ Successfully imported {added_count} products!', 'success')
    return redirect(url_for('stock_in.stock_in_page'))
