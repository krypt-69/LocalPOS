"""
Helper functions for LocalPOS
"""

from datetime import datetime, date
import re

def format_currency(amount):
    """Format amount as KSh"""
    return f"KSh {amount:,.2f}"

def calculate_profit(buying_price, selling_price, quantity=1):
    """Calculate profit per item and total"""
    profit_per_item = selling_price - buying_price
    total_profit = profit_per_item * quantity
    return {
        'per_item': profit_per_item,
        'total': total_profit
    }

def validate_prices(buying_price, selling_price):
    """Validate prices - warning if selling below cost"""
    if selling_price < buying_price:
        return {
            'valid': False,
            'warning': f'Selling price ({format_currency(selling_price)}) is below buying price ({format_currency(buying_price)})! This will result in loss.'
        }
    return {'valid': True, 'warning': None}

def generate_receipt_number():
    """Generate unique receipt number"""
    now = datetime.now()
    return f"INV-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

def sanitize_text(text):
    """Remove special characters from text"""
    if not text:
        return ''
    return re.sub(r'[^\w\s-]', '', text)

def parse_date(date_string):
    """Parse date from various formats"""
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except:
        return date.today()
