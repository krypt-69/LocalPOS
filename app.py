"""
LocalPOS - Main Flask Application
Stock management system for local businesses
"""

from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from database.models import db, User
from werkzeug.security import check_password_hash
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

# Fix: Use absolute path for database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database', 'localpos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads', 'products')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(basedir, 'database'), exist_ok=True)

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import routes (after app initialization to avoid circular imports)
from routes import auth, dashboard, stock_in, stock_out, stock_management, debtors, reports
from routes import categories

# Register blueprints
app.register_blueprint(auth.auth_bp)
app.register_blueprint(dashboard.dashboard_bp)
app.register_blueprint(stock_in.stock_in_bp)
app.register_blueprint(stock_out.stock_out_bp)
app.register_blueprint(stock_management.stock_bp)
app.register_blueprint(debtors.debtors_bp)
app.register_blueprint(reports.reports_bp)
app.register_blueprint(categories.categories_bp)

@app.route('/')
def index():
    """Redirect to dashboard or login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard_home'))
    return redirect(url_for('auth.login'))

# CLI command to initialize database
@app.cli.command('init-db')
def init_db_command():
    """Initialize database with tables and default data"""
    from database.db_init import init_database
    init_database(app)
    print("Database initialized successfully!")

if __name__ == '__main__':
    # Create database if it doesn't exist
    with app.app_context():
        db.create_all()
        print(f"✅ Database created at: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Run app on local network
    app.run(host='0.0.0.0', port=5000, debug=True)
