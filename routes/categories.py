"""
Categories Management routes - Add, edit, delete categories
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from database.models import db, Category, Product

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')

@categories_bp.route('/')
@login_required
def manage_categories():
    """Category management page"""
    categories = Category.query.order_by(Category.name).all()
    
    # Get product count for each category
    for cat in categories:
        cat.product_count = Product.query.filter_by(category_id=cat.id).count()
    
    return render_template('categories.html', categories=categories)

@categories_bp.route('/add', methods=['POST'])
@login_required
def add_category():
    """Add new category"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('categories.manage_categories'))
    
    # Check if category already exists
    existing = Category.query.filter_by(name=name).first()
    if existing:
        flash(f'Category "{name}" already exists!', 'warning')
        return redirect(url_for('categories.manage_categories'))
    
    category = Category(name=name, description=description)
    db.session.add(category)
    db.session.commit()
    
    flash(f'✅ Category "{name}" added successfully!', 'success')
    return redirect(url_for('categories.manage_categories'))

@categories_bp.route('/edit/<int:category_id>', methods=['POST'])
@login_required
def edit_category(category_id):
    """Edit existing category"""
    category = Category.query.get_or_404(category_id)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('categories.manage_categories'))
    
    # Check if name conflicts with another category
    existing = Category.query.filter(Category.name == name, Category.id != category_id).first()
    if existing:
        flash(f'Category "{name}" already exists!', 'warning')
        return redirect(url_for('categories.manage_categories'))
    
    category.name = name
    category.description = description
    db.session.commit()
    
    flash(f'✅ Category "{name}" updated successfully!', 'success')
    return redirect(url_for('categories.manage_categories'))

@categories_bp.route('/delete/<int:category_id>')
@login_required
def delete_category(category_id):
    """Delete category (only if no products linked)"""
    category = Category.query.get_or_404(category_id)
    
    # Check if category has products
    product_count = Product.query.filter_by(category_id=category_id).count()
    
    if product_count > 0:
        flash(f'❌ Cannot delete "{category.name}" - {product_count} product(s) belong to this category!', 'danger')
        return redirect(url_for('categories.manage_categories'))
    
    name = category.name
    db.session.delete(category)
    db.session.commit()
    
    flash(f'✅ Category "{name}" deleted successfully!', 'success')
    return redirect(url_for('categories.manage_categories'))

@categories_bp.route('/api/list')
@login_required
def api_list_categories():
    """JSON endpoint for category list (for AJAX)"""
    categories = Category.query.order_by(Category.name).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'description': c.description
    } for c in categories])
