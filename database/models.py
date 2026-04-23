"""
Database Models for LocalPOS
All tables defined with relationships
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """System users (max 2 users)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    stock_entries = db.relationship('StockEntry', backref='user', lazy=True)
    sales = db.relationship('Sale', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)

class Category(db.Model):
    """Product categories (dynamic - user can add/edit/delete)"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    """Main product table"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    current_stock = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=5)
    buying_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    unit_type = db.Column(db.String(50), default='piece')  # piece, crate, kg, meter
    unit_conversion = db.Column(db.Integer, default=1)  # e.g., 1 crate = 24 bottles
    image_filename = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    variants = db.relationship('ProductVariant', backref='product', lazy=True)
    stock_entries = db.relationship('StockEntry', backref='product', lazy=True)
    sale_items = db.relationship('SaleItem', backref='product', lazy=True)

class ProductVariant(db.Model):
    """For products with sizes/colors (clothes, curtains)"""
    __tablename__ = 'product_variants'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_name = db.Column(db.String(100), nullable=False)  # e.g., "Red - Size M"
    sku = db.Column(db.String(100), unique=True)
    current_stock = db.Column(db.Integer, default=0)
    extra_cost = db.Column(db.Float, default=0.0)  # Extra cost for this variant
    
class StockEntry(db.Model):
    """Record of all stock coming in"""
    __tablename__ = 'stock_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier = db.Column(db.String(200))
    notes = db.Column(db.Text)
    entry_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
class Sale(db.Model):
    """Main sales table"""
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    final_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, mpesa, credit
    amount_paid = db.Column(db.Float, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    items = db.relationship('SaleItem', backref='sale', lazy=True)
    debtor = db.relationship('Debtor', backref='sale', uselist=False)

class SaleItem(db.Model):
    """Individual items in a sale"""
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_sale = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)

class Debtor(db.Model):
    """Credit sales tracking"""
    __tablename__ = 'debtors'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    total_owed = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, partial, overdue, paid
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payments = db.relationship('Payment', backref='debtor', lazy=True)

class Payment(db.Model):
    """Payments made against debts"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    debtor_id = db.Column(db.Integer, db.ForeignKey('debtors.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, mpesa
    notes = db.Column(db.Text)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
