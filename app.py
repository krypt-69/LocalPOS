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

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database', 'localpos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads', 'products')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(basedir, 'database'), exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom Jinja filter for currency formatting with commas
@app.template_filter('format_currency')
def format_currency_filter(amount):
    if amount is None:
        return "KSh 0.00"
    try:
        return f"KSh {amount:,.2f}"
    except (TypeError, ValueError):
        return "KSh 0.00"

from routes import auth, dashboard, stock_in, stock_out, stock_management, debtors, reports, categories
from routes import users

from routes import services
from routes import users
from routes import activity

app.register_blueprint(activity.activity_bp)
app.register_blueprint(auth.auth_bp)
app.register_blueprint(dashboard.dashboard_bp)
app.register_blueprint(stock_in.stock_in_bp)
app.register_blueprint(stock_out.stock_out_bp)
app.register_blueprint(stock_management.stock_bp)
app.register_blueprint(debtors.debtors_bp)
app.register_blueprint(reports.reports_bp)
app.register_blueprint(categories.categories_bp)
app.register_blueprint(services.services_bp)
app.register_blueprint(users.users_bp)


def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard_home'))
    return redirect(url_for('auth.login'))

@app.cli.command('init-db')
def init_db_command():
    from database.db_init import init_database
    init_database(app)
    print("Database initialized successfully!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print(f"✅ Database created at: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(host='0.0.0.0', port=5000, debug=True)
