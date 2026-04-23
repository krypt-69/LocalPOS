"""
Form validation utilities
"""

def validate_stock_entry(product_name, quantity, buying_price, selling_price):
    """Validate stock entry form data"""
    errors = []
    
    if not product_name or len(product_name.strip()) < 2:
        errors.append("Product name must be at least 2 characters")
    
    try:
        qty = int(quantity)
        if qty <= 0:
            errors.append("Quantity must be greater than 0")
    except:
        errors.append("Quantity must be a valid number")
    
    try:
        buy_price = float(buying_price)
        if buy_price < 0:
            errors.append("Buying price cannot be negative")
    except:
        errors.append("Buying price must be a valid number")
    
    try:
        sell_price = float(selling_price)
        if sell_price < 0:
            errors.append("Selling price cannot be negative")
    except:
        errors.append("Selling price must be a valid number")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
