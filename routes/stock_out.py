"""
Stock Out routes - Sales processing (POS + Form modes)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from database.models import db, Product, Category, Sale, SaleItem, Debtor, StockEntry
from utils.helpers import generate_receipt_number, format_currency, calculate_profit
from datetime import datetime, date
import json

stock_out_bp = Blueprint('stock_out', __name__, url_prefix='/stock-out')

@stock_out_bp.route('/')
@login_required
def stock_out_page():
    """Stock Out main page with mode toggle"""
    categories = Category.query.all()
    products = Product.query.filter(Product.current_stock > 0, Product.is_active == True).order_by(Product.name).all()
    
    # Get cart from session
    cart = session.get('sale_cart', [])
    
    return render_template('stock_out.html', 
                         categories=categories,
                         products=products,
                         cart=cart,
                         format_currency=format_currency)

@stock_out_bp.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart"""
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    price_override = request.form.get('price_override', type=float)
    
    product = Product.query.get_or_404(product_id)
    
    # Check stock availability
    if quantity > product.current_stock:
        return jsonify({
            'success': False,
            'error': f'Only {product.current_stock} items available'
        })
    
    # Get cart from session
    cart = session.get('sale_cart', [])
    
    # Check if product already in cart
    for item in cart:
        if item['product_id'] == product_id:
            # Update quantity
            new_qty = item['quantity'] + quantity
            if new_qty > product.current_stock:
                return jsonify({
                    'success': False,
                    'error': f'Total {new_qty} exceeds stock {product.current_stock}'
                })
            item['quantity'] = new_qty
            break
    else:
        # Add new item
        cart.append({
            'product_id': product.id,
            'name': product.name,
            'quantity': quantity,
            'price': price_override if price_override else product.selling_price,
            'stock': product.current_stock
        })
    
    session['sale_cart'] = cart
    session.modified = True
    
    # Calculate cart total
    total = sum(item['quantity'] * item['price'] for item in cart)
    
    return jsonify({
        'success': True,
        'cart': cart,
        'total': total,
        'item_count': len(cart)
    })

@stock_out_bp.route('/remove-from-cart/<int:index>')
@login_required
def remove_from_cart(index):
    """Remove item from cart"""
    cart = session.get('sale_cart', [])
    if 0 <= index < len(cart):
        cart.pop(index)
    session['sale_cart'] = cart
    session.modified = True
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity"""
    data = request.get_json()
    index = data.get('index')
    quantity = int(data.get('quantity', 1))
    
    cart = session.get('sale_cart', [])
    
    if 0 <= index < len(cart):
        product_id = cart[index]['product_id']
        product = Product.query.get(product_id)
        
        if quantity > product.current_stock:
            return jsonify({
                'success': False,
                'error': f'Only {product.current_stock} items available'
            })
        
        cart[index]['quantity'] = quantity
        session['sale_cart'] = cart
        session.modified = True
    
    total = sum(item['quantity'] * item['price'] for item in cart)
    
    return jsonify({
        'success': True,
        'total': total,
        'cart': cart
    })

@stock_out_bp.route('/clear-cart')
@login_required
def clear_cart():
    """Clear entire cart"""
    session.pop('sale_cart', None)
    flash('Cart cleared', 'info')
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """Process the sale"""
    cart = session.get('sale_cart', [])
    
    if not cart:
        flash('Cart is empty', 'danger')
        return redirect(url_for('stock_out.stock_out_page'))
    
    # Get payment details
    payment_method = request.form.get('payment_method')
    amount_paid = float(request.form.get('amount_paid', 0))
    discount_type = request.form.get('discount_type')
    discount_value = float(request.form.get('discount_value', 0))
    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    due_date = request.form.get('due_date', '')
    notes = request.form.get('notes', '')
    
    # Calculate totals
    subtotal = sum(item['quantity'] * item['price'] for item in cart)
    
    # Apply discount
    if discount_type == 'percentage':
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == 'fixed':
        discount_amount = discount_value
    else:
        discount_amount = 0
    
    final_amount = subtotal - discount_amount
    
    # Validate payment
    if payment_method != 'credit' and amount_paid < final_amount:
        flash(f'Amount paid (KSh {amount_paid}) is less than total (KSh {final_amount})', 'danger')
        return redirect(url_for('stock_out.stock_out_page'))
    
    balance = final_amount - amount_paid if payment_method == 'credit' else 0
    
    try:
        # Create sale record
        receipt_number = generate_receipt_number()
        sale = Sale(
            receipt_number=receipt_number,
            total_amount=subtotal,
            discount=discount_amount,
            final_amount=final_amount,
            payment_method=payment_method,
            amount_paid=amount_paid,
            balance=balance,
            customer_name=customer_name if payment_method == 'credit' else None,
            customer_phone=customer_phone if payment_method == 'credit' else None,
            notes=notes,
            user_id=current_user.id
        )
        db.session.add(sale)
        db.session.flush()
        
        # Process each item
        for item in cart:
            product = Product.query.get(item['product_id'])
            
            # Check stock again
            if item['quantity'] > product.current_stock:
                db.session.rollback()
                flash(f'Insufficient stock for {product.name}. Available: {product.current_stock}', 'danger')
                return redirect(url_for('stock_out.stock_out_page'))
            
            # Reduce stock
            product.current_stock -= item['quantity']
            
            # Create sale item
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=item['quantity'],
                price_at_sale=item['price'],
                total=item['quantity'] * item['price']
            )
            db.session.add(sale_item)
        
        # Handle credit sale
        if payment_method == 'credit' and balance > 0:
            debtor = Debtor(
                sale_id=sale.id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                total_owed=final_amount,
                amount_paid=amount_paid,
                balance=balance,
                due_date=datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None,
                status='pending',
                notes=notes
            )
            db.session.add(debtor)
        
        db.session.commit()
        
        # Clear cart
        session.pop('sale_cart', None)
        
        # Prepare receipt data
        receipt_data = {
            'receipt_number': receipt_number,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'items': cart,
            'subtotal': subtotal,
            'discount': discount_amount,
            'total': final_amount,
            'paid': amount_paid,
            'balance': balance,
            'payment_method': payment_method,
            'customer_name': customer_name if payment_method == 'credit' else None,
            'cashier': current_user.username
        }
        
        flash(f'Sale completed! Receipt: {receipt_number}', 'success')
        
        # Store receipt in session for display
        session['last_receipt'] = receipt_data
        
        return redirect(url_for('stock_out.receipt', receipt_id=sale.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing sale: {str(e)}', 'danger')
        return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/receipt/<int:receipt_id>')
@login_required
def receipt(receipt_id):
    """View receipt"""
    sale = Sale.query.get_or_404(receipt_id)
    items = SaleItem.query.filter_by(sale_id=receipt_id).all()
    
    return render_template('receipt.html', sale=sale, items=items, format_currency=format_currency)

@stock_out_bp.route('/hold-sale', methods=['POST'])
@login_required
def hold_sale():
    """Hold current sale for later"""
    cart = session.get('sale_cart', [])
    if cart:
        session['held_sale'] = {
            'cart': cart,
            'timestamp': datetime.now().isoformat()
        }
        session.pop('sale_cart', None)
        flash('Sale held. You can resume it later.', 'success')
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/resume-sale')
@login_required
def resume_sale():
    """Resume held sale"""
    held = session.get('held_sale')
    if held:
        session['sale_cart'] = held['cart']
        session.pop('held_sale', None)
        flash('Held sale resumed', 'success')
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/api/products')
@login_required
def api_products():
    """API endpoint for products (for POS mode)"""
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    
    query = Product.query.filter(Product.current_stock > 0, Product.is_active == True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.limit(50).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': p.selling_price,
        'stock': p.current_stock,
        'category': p.category.name
    } for p in products])

@stock_out_bp.route('/api/product/<int:product_id>')
@login_required
def api_product_detail(product_id):
    """Get single product details"""
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': product.selling_price,
        'stock': product.current_stock,
        'buying_price': product.buying_price,
        'profit': product.selling_price - product.buying_price
    })
