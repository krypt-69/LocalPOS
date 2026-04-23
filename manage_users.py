#!/usr/bin/env python3
"""
User Management Script for LocalPOS
Create, list, reset passwords, and delete users
"""

import sys
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database.models import db, User

def create_user(username, password, full_name):
    """Create a new user"""
    with app.app_context():
        # Check if user exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"❌ User '{username}' already exists!")
            return False
        
        # Create new user
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        print(f"✅ User '{username}' created successfully!")
        print(f"   Full Name: {full_name}")
        print(f"   Password: {password}")
        return True

def list_users():
    """List all users"""
    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found.")
            return
        
        print("\n" + "="*60)
        print(f"{'ID':<5} {'Username':<15} {'Full Name':<25} {'Status':<10}")
        print("="*60)
        for user in users:
            status = "Active" if user.is_active else "Inactive"
            print(f"{user.id:<5} {user.username:<15} {user.full_name:<25} {status:<10}")
        print("="*60 + "\n")

def reset_password(username, new_password):
    """Reset user password"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"✅ Password for '{username}' reset successfully!")
        print(f"   New password: {new_password}")
        return True

def delete_user(username):
    """Delete a user (cannot delete last user)"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        
        # Check if this is the last user
        user_count = User.query.count()
        if user_count <= 1:
            print(f"❌ Cannot delete the last user!")
            return False
        
        db.session.delete(user)
        db.session.commit()
        print(f"✅ User '{username}' deleted successfully!")
        return True

def set_active(username, active=True):
    """Activate or deactivate a user"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        
        user.is_active = active
        db.session.commit()
        status = "activated" if active else "deactivated"
        print(f"✅ User '{username}' {status} successfully!")
        return True

def show_help():
    """Display help information"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              LocalPOS User Management Tool                   ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
    python manage_users.py <command> [arguments]

COMMANDS:
    create <username> <password> <full_name>    Create a new user
    list                                        List all users
    reset <username> <new_password>             Reset user password
    delete <username>                           Delete a user
    activate <username>                         Activate a user
    deactivate <username>                       Deactivate a user
    help                                        Show this help

EXAMPLES:
    python manage_users.py create john pass123 "John Doe"
    python manage_users.py list
    python manage_users.py reset john newpass456
    python manage_users.py delete john
    python manage_users.py activate john

DEFAULT USERS:
    user1 / password123
    user2 / password123
""")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'create':
        if len(sys.argv) < 5:
            print("Usage: python manage_users.py create <username> <password> <full_name>")
            return
        create_user(sys.argv[2], sys.argv[3], sys.argv[4])
    
    elif command == 'list':
        list_users()
    
    elif command == 'reset':
        if len(sys.argv) < 4:
            print("Usage: python manage_users.py reset <username> <new_password>")
            return
        reset_password(sys.argv[2], sys.argv[3])
    
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("Usage: python manage_users.py delete <username>")
            return
        delete_user(sys.argv[2])
    
    elif command == 'activate':
        if len(sys.argv) < 3:
            print("Usage: python manage_users.py activate <username>")
            return
        set_active(sys.argv[2], True)
    
    elif command == 'deactivate':
        if len(sys.argv) < 3:
            print("Usage: python manage_users.py deactivate <username>")
            return
        set_active(sys.argv[2], False)
    
    elif command == 'help':
        show_help()
    
    else:
        print(f"Unknown command: {command}")
        show_help()

if __name__ == '__main__':
    main()
