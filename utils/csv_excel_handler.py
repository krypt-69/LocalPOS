"""
CSV and Excel import/export handling using Pandas
"""

import pandas as pd
import os
from flask import flash
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def import_products_from_file(file_path, file_type):
    """
    Import products from CSV or Excel file
    Expected columns: name, category, quantity, buying_price, selling_price, supplier
    """
    try:
        if file_type == 'csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Standardize column names (lowercase, strip spaces)
        df.columns = df.columns.str.lower().str.strip()
        
        # Check required columns
        required = ['name', 'category', 'quantity', 'buying_price', 'selling_price']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            return {
                'success': False,
                'error': f'Missing columns: {", ".join(missing)}. Found: {list(df.columns)}'
            }
        
        # Convert to dictionary list
        products = df.to_dict('records')
        
        return {
            'success': True,
            'products': products,
            'count': len(products)
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def export_to_csv(data, filename):
    """Export data to CSV"""
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    return filename

def export_to_excel(data, filename):
    """Export data to Excel"""
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    return filename

def preview_import_file(file):
    """Preview first 5 rows of import file"""
    if not allowed_file(file.filename):
        return None, "File type not allowed. Use CSV or Excel."
    
    filename = secure_filename(file.filename)
    file_type = filename.rsplit('.', 1)[1].lower()
    
    try:
        if file_type == 'csv':
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Reset file pointer for later use
        file.seek(0)
        
        # Return preview as HTML table
        preview_html = df.head().to_html(classes='table table-sm table-bordered', index=False)
        
        return {
            'html': preview_html,
            'columns': list(df.columns),
            'rows': len(df)
        }, None
    
    except Exception as e:
        return None, str(e)
