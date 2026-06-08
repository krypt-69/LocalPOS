#!/usr/bin/env python3
import sys
import os
from werkzeug.security import generate_password_hash
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
from database.models import db, User

def create_user(username, password, full_name, role='worker'):
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"❌ User '{username}' already exists!")
            return False
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            role=role,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        print(f"✅ User '{username}' created! Role: {role}")
        return True

def list_users():
    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found.")
            return
        print("\n" + "="*70)
        print(f"{'ID':<5} {'Username':<15} {'Full Name':<25} {'Role':<10} {'Active':<8}")
        print("="*70)
        for u in users:
            active = "Yes" if u.is_active else "No"
            print(f"{u.id:<5} {u.username:<15} {u.full_name:<25} {u.role:<10} {active:<8}")
        print("="*70 + "\n")

def reset_password(username, new_password):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"✅ Password for '{username}' reset.")
        return True

def set_role(username, new_role):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        user.role = new_role
        db.session.commit()
        print(f"✅ Role for '{username}' changed to {new_role}")
        return True

def delete_user(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        if User.query.count() <= 1:
            print("❌ Cannot delete the last user!")
            return False
        db.session.delete(user)
        db.session.commit()
        print(f"✅ User '{username}' deleted.")
        return True

def set_active(username, active=True):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found!")
            return False
        user.is_active = active
        db.session.commit()
        status = "activated" if active else "deactivated"
        print(f"✅ User '{username}' {status}.")
        return True

def show_help():
    print("""
LocalPOS User Management
=======================
Commands:
  create <username> <password> <full_name> [role]   Create user (role: owner/admin/worker)
  list                                             List all users
  reset <username> <new_password>                  Reset password
  set-role <username> <role>                       Change role
  activate <username>                              Activate user
  deactivate <username>                            Deactivate user
  delete <username>                                Delete user
  help                                             This help

Examples:
  python manage_users.py create john pass123 "John Doe" worker
  python manage_users.py set-role mary owner
""")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    cmd = sys.argv[1].lower()
    if cmd == 'create':
        if len(sys.argv) < 5:
            print("Usage: create <username> <password> <full_name> [role]")
            return
        role = sys.argv[5] if len(sys.argv) > 5 else 'worker'
        create_user(sys.argv[2], sys.argv[3], sys.argv[4], role)
    elif cmd == 'list':
        list_users()
    elif cmd == 'reset':
        if len(sys.argv) < 4:
            print("Usage: reset <username> <new_password>")
            return
        reset_password(sys.argv[2], sys.argv[3])
    elif cmd == 'set-role':
        if len(sys.argv) < 4:
            print("Usage: set-role <username> <role>")
            return
        set_role(sys.argv[2], sys.argv[3])
    elif cmd == 'delete':
        if len(sys.argv) < 3:
            print("Usage: delete <username>")
            return
        delete_user(sys.argv[2])
    elif cmd == 'activate':
        if len(sys.argv) < 3:
            print("Usage: activate <username>")
            return
        set_active(sys.argv[2], True)
    elif cmd == 'deactivate':
        if len(sys.argv) < 3:
            print("Usage: deactivate <username>")
            return
        set_active(sys.argv[2], False)
    else:
        show_help()

if __name__ == '__main__':
    main()
