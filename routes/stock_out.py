from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from database.models import db, Product, Category, Sale, SaleItem, Debtor, StockEntry
from utils.helpers import generate_receipt_number, format_currency, calculate_profit
from utils.activity_logger import log_activity
from datetime import datetime, date
import json

stock_out_bp = Blueprint('stock_out', __name__, url_prefix='/stock-out')

@stock_out_bp.route('/')
@login_required
def stock_out_page():
    categories = Category.query.all()
    products = Product.query.filter(Product.current_stock > 0, Product.is_active == True).order_by(Product.name).all()
    cart = session.get('sale_cart', [])
    subtotal = sum(item['quantity'] * item['price'] for item in cart)
    total = subtotal
    return render_template('stock_out.html', 
                         categories=categories, 
                         products=products, 
                         cart=cart, 
                         format_currency=format_currency,
                         subtotal=subtotal,
                         total=total)

@stock_out_bp.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    price_override = request.form.get('price_override', type=float)
    product = Product.query.get_or_404(product_id)
    if quantity > product.current_stock:
        return jsonify({'success': False, 'error': f'Only {product.current_stock} items available'})
    cart = session.get('sale_cart', [])
    for item in cart:
        if item['product_id'] == product_id:
            new_qty = item['quantity'] + quantity
            if new_qty > product.current_stock:
                return jsonify({'success': False, 'error': f'Total {new_qty} exceeds stock {product.current_stock}'})
            item['quantity'] = new_qty
            break
    else:
        cart.append({'product_id': product.id, 'name': product.name, 'quantity': quantity, 'price': price_override if price_override else product.selling_price, 'stock': product.current_stock})
    session['sale_cart'] = cart
    session.modified = True
    total = sum(item['quantity'] * item['price'] for item in cart)
    return jsonify({'success': True, 'cart': cart, 'total': total, 'item_count': len(cart)})

@stock_out_bp.route('/remove-from-cart/<int:index>')
@login_required
def remove_from_cart(index):
    cart = session.get('sale_cart', [])
    if 0 <= index < len(cart):
        cart.pop(index)
    session['sale_cart'] = cart
    session.modified = True
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    index = data.get('index')
    quantity = int(data.get('quantity', 1))
    cart = session.get('sale_cart', [])
    if 0 <= index < len(cart):
        product_id = cart[index]['product_id']
        product = Product.query.get(product_id)
        if quantity > product.current_stock:
            return jsonify({'success': False, 'error': f'Only {product.current_stock} items available'})
        cart[index]['quantity'] = quantity
        session['sale_cart'] = cart
        session.modified = True
    total = sum(item['quantity'] * item['price'] for item in cart)
    return jsonify({'success': True, 'total': total, 'cart': cart})

@stock_out_bp.route('/clear-cart')
@login_required
def clear_cart():
    session.pop('sale_cart', None)
    flash('Cart cleared', 'info')
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart = session.get('sale_cart', [])
    if not cart:
        flash('Cart is empty', 'danger')
        return redirect(url_for('stock_out.stock_out_page'))
    payment_method = request.form.get('payment_method')
    amount_paid = float(request.form.get('amount_paid', 0))
    discount_type = request.form.get('discount_type')
    discount_value = float(request.form.get('discount_value', 0))
    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    due_date = request.form.get('due_date', '')
    notes = request.form.get('notes', '')
    subtotal = sum(item['quantity'] * item['price'] for item in cart)
    if discount_type == 'percentage':
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == 'fixed':
        discount_amount = discount_value
    else:
        discount_amount = 0
    final_amount = subtotal - discount_amount
    if payment_method != 'credit' and amount_paid < final_amount:
        flash(f'Amount paid (KSh {amount_paid}) is less than total (KSh {final_amount})', 'danger')
        return redirect(url_for('stock_out.stock_out_page'))
    balance = final_amount - amount_paid if payment_method == 'credit' else 0
    try:
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
        for item in cart:
            product = Product.query.get(item['product_id'])
            if item['quantity'] > product.current_stock:
                db.session.rollback()
                flash(f'Insufficient stock for {product.name}. Available: {product.current_stock}', 'danger')
                return redirect(url_for('stock_out.stock_out_page'))
            product.current_stock -= item['quantity']
            sale_item = SaleItem(sale_id=sale.id, product_id=product.id, quantity=item['quantity'], price_at_sale=item['price'], total=item['quantity'] * item['price'])
            db.session.add(sale_item)
        if payment_method == 'credit' and balance > 0:
            debtor = Debtor(
                sale_id=sale.id,
                source='sale',
                source_id=sale.id,
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
        log_activity('sale', f"Sale {receipt_number}: {len(cart)} items, total {final_amount:,.2f}, payment: {payment_method}", 'sale', sale.id)
        if discount_amount > 0:
            log_activity('discount', f"Discount {discount_value}{'%' if discount_type=='percentage' else 'fixed'} applied on sale {receipt_number}", 'sale', sale.id)
        if payment_method == 'credit' and balance > 0:
            log_activity('credit_sale', f"Credit sale {receipt_number} to {customer_name}, balance {balance:,.2f}", 'debtor', debtor.id)
        session.pop('sale_cart', None)
        flash(f'Sale completed! Receipt: {receipt_number}', 'success')
        return redirect(url_for('stock_out.receipt', receipt_id=sale.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing sale: {str(e)}', 'danger')
        return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/receipt/<int:receipt_id>')
@login_required
def receipt(receipt_id):
    sale = Sale.query.get_or_404(receipt_id)
    items = SaleItem.query.filter_by(sale_id=receipt_id).all()
    return render_template('receipt.html', sale=sale, items=items, format_currency=format_currency)

@stock_out_bp.route('/hold-sale', methods=['POST'])
@login_required
def hold_sale():
    cart = session.get('sale_cart', [])
    if cart:
        session['held_sale'] = {'cart': cart, 'timestamp': datetime.now().isoformat()}
        session.pop('sale_cart', None)
        flash('Sale held. You can resume it later.', 'success')
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/resume-sale')
@login_required
def resume_sale():
    held = session.get('held_sale')
    if held:
        session['sale_cart'] = held['cart']
        session.pop('held_sale', None)
        flash('Held sale resumed', 'success')
    return redirect(url_for('stock_out.stock_out_page'))

@stock_out_bp.route('/api/products')
@login_required
def api_products():
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    query = Product.query.filter(Product.current_stock > 0, Product.is_active == True)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    products = query.limit(50).all()
    return jsonify([{'id': p.id, 'name': p.name, 'price': p.selling_price, 'stock': p.current_stock, 'category': p.category.name} for p in products])

@stock_out_bp.route('/api/product/<int:product_id>')
@login_required
def api_product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({'id': product.id, 'name': product.name, 'price': product.selling_price, 'stock': product.current_stock, 'buying_price': product.buying_price, 'profit': product.selling_price - product.buying_price})
