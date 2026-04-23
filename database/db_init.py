"""
Database initialization script
Run once to create all tables and seed default data
"""

from database.models import db, User, Category
from werkzeug.security import generate_password_hash
from flask import Flask
import os

def init_database(app):
    """Initialize database with tables and default data"""
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created")
        
        # Check if users exist
        if User.query.count() == 0:
            # Create default users
            user1 = User(
                username='user1',
                password_hash=generate_password_hash('password123'),
                full_name='User One'
            )
            user2 = User(
                username='user2',
                password_hash=generate_password_hash('password123'),
                full_name='User Two'
            )
            db.session.add_all([user1, user2])
            db.session.commit()
            print("✅ Default users created (user1/password123, user2/password123)")
        
        # Check if categories exist
        if Category.query.count() == 0:
            default_categories = [
                Category(name='Electronics', description='TVs, phones, appliances'),
                Category(name='Curtains', description='All curtain types'),
                Category(name='Clothes', description='Dresses, shirts, trousers'),
                Category(name='Drinks', description='Soda, water, juice')
            ]
            db.session.add_all(default_categories)
            db.session.commit()
            print("✅ Default categories created")
        
        print("🎉 Database initialization complete!")

if __name__ == '__main__':
    print("Run this from app.py instead")
    print("Use: python app.py init-db")
