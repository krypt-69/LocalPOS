from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.models import db, Category, Product
from utils.role_helpers import role_required

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')

@categories_bp.route('/')
@login_required
@role_required('owner', 'admin')
def manage_categories():
    categories = Category.query.order_by(Category.name).all()
    for cat in categories:
        cat.product_count = Product.query.filter_by(category_id=cat.id).count()
    return render_template('categories.html', categories=categories)

@categories_bp.route('/add', methods=['POST'])
@login_required
@role_required('owner', 'admin')
def add_category():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    max_discount = float(request.form.get('max_discount_percent', 0))
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('categories.manage_categories'))
    if Category.query.filter_by(name=name).first():
        flash(f'Category "{name}" already exists!', 'warning')
        return redirect(url_for('categories.manage_categories'))
    category = Category(name=name, description=description, max_discount_percent=max_discount)
    db.session.add(category)
    db.session.commit()
    flash(f'✅ Category "{name}" added successfully!', 'success')
    return redirect(url_for('categories.manage_categories'))

@categories_bp.route('/edit/<int:category_id>', methods=['POST'])
@login_required
@role_required('owner', 'admin')
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    max_discount = float(request.form.get('max_discount_percent', 0))
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('categories.manage_categories'))
    existing = Category.query.filter(Category.name == name, Category.id != category_id).first()
    if existing:
        flash(f'Category "{name}" already exists!', 'warning')
        return redirect(url_for('categories.manage_categories'))
    category.name = name
    category.description = description
    category.max_discount_percent = max_discount
    db.session.commit()
    flash(f'✅ Category "{name}" updated successfully!', 'success')
    return redirect(url_for('categories.manage_categories'))

@categories_bp.route('/delete/<int:category_id>')
@login_required
@role_required('owner', 'admin')
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
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
    categories = Category.query.order_by(Category.name).all()
    return jsonify([{'id': c.id, 'name': c.name, 'description': c.description, 'max_discount': c.max_discount_percent} for c in categories])
