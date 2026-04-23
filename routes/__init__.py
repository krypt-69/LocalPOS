"""
Routes package initialization
All blueprints are imported here
"""

from routes import auth
from routes import dashboard
from routes import stock_in
from routes import stock_out
from routes import stock_management
from routes import debtors
from routes import reports
from routes import categories

__all__ = ['auth', 'dashboard', 'stock_in', 'stock_out', 'stock_management', 'debtors', 'reports', 'categories']
