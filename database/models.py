"""
Database Models for LocalPOS
All tables defined with relationships
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='worker')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    stock_entries = db.relationship('StockEntry', backref='user', lazy=True)
    sales = db.relationship('Sale', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    service_jobs = db.relationship('ServiceJob', backref='creator', lazy=True)
    service_history = db.relationship('ServiceHistory', backref='user', lazy=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    max_discount_percent = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    current_stock = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=5)
    buying_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    unit_type = db.Column(db.String(50), default='piece')
    unit_conversion = db.Column(db.Integer, default=1)
    image_filename = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    variants = db.relationship('ProductVariant', backref='product', lazy=True)
    stock_entries = db.relationship('StockEntry', backref='product', lazy=True)
    sale_items = db.relationship('SaleItem', backref='product', lazy=True)

class ProductVariant(db.Model):
    __tablename__ = 'product_variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(100), unique=True)
    current_stock = db.Column(db.Integer, default=0)
    extra_cost = db.Column(db.Float, default=0.0)

class StockEntry(db.Model):
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
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    final_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    items = db.relationship('SaleItem', backref='sale', lazy=True)
    debtor = db.relationship('Debtor', backref='sale', uselist=False)

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_sale = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)

class Debtor(db.Model):
    __tablename__ = 'debtors'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    source = db.Column(db.String(20), default='sale')   # 'sale', 'service', 'contract'
    source_id = db.Column(db.Integer, nullable=True)    # ID of the source record (sale.id or service_job.id)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    total_owed = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payments = db.relationship('Payment', backref='debtor', lazy=True)
    # For service jobs, we'll link via source='service' and source_id

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    debtor_id = db.Column(db.Integer, db.ForeignKey('debtors.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# ==================== Services Module ====================

class ServiceCategory(db.Model):
    __tablename__ = 'service_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    service_types = db.relationship('ServiceType', backref='category', lazy=True)

class ServiceType(db.Model):
    __tablename__ = 'service_types'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    max_charge = db.Column(db.Float, default=0.0)   # 0 means no limit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    jobs = db.relationship('ServiceJob', backref='service_type', lazy=True)

class ServiceJob(db.Model):
    __tablename__ = 'service_jobs'
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'), nullable=False)
    service_category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'), nullable=False)
    item_description = db.Column(db.String(200), nullable=False)
    issue_description = db.Column(db.Text)
    status = db.Column(db.String(20), default='received')
    expected_completion_date = db.Column(db.Date, nullable=True)
    service_charge = db.Column(db.Float, default=0.0)
    parts_cost = db.Column(db.Float, default=0.0)
    total_cost = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='unpaid')
    notes = db.Column(db.Text)
    technician_notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    collected_at = db.Column(db.DateTime, nullable=True)

    history = db.relationship('ServiceHistory', backref='job', lazy=True)

class ServiceHistory(db.Model):
    __tablename__ = 'service_history'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('service_jobs.id'), nullable=False)
    status_from = db.Column(db.String(20))
    status_to = db.Column(db.String(20))
    notes = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)





class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='activities')
