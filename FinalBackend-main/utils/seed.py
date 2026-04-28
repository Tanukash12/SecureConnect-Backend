"""
Seed initial users into MongoDB
Run on first startup automatically via app.py
"""
from werkzeug.security import generate_password_hash
from config.db import mongo
from utils.helpers import get_ist_now
from flask import current_app


def seed_users():
    db = mongo.db

    # -------- Admin --------
    if not db.users.find_one({'username': 'admin'}):
        admin_password = current_app.config.get('ADMIN_PASSWORD', 'admin123')
        db.users.insert_one({
            'username': 'admin',
            'email': 'admin@company.com',
            'password': generate_password_hash(admin_password),
            'full_name': 'System Administrator',
            'department': 'IT',
            'role': 'admin',
            'is_active': True,
            'is_online': False,
            'risk_score': 0,
            'avatar_color': '#dc3545',
            'created_at': get_ist_now()
        })
        print('✅ Admin user created  →  username: admin')

    # -------- Sample Employees --------
    sample_users = [
        {'username': 'john',  'email': 'john@company.com',  'full_name': 'John Doe',      'department': 'Engineering', 'color': '#667eea'},
        {'username': 'sarah', 'email': 'sarah@company.com', 'full_name': 'Sarah Smith',   'department': 'Marketing',   'color': '#764ba2'},
        {'username': 'mike',  'email': 'mike@company.com',  'full_name': 'Mike Johnson',  'department': 'Sales',       'color': '#f093fb'},
    ]

    for u in sample_users:
        if not db.users.find_one({'username': u['username']}):
            db.users.insert_one({
                'username': u['username'],
                'email': u['email'],
                'password': generate_password_hash('password123'),
                'full_name': u['full_name'],
                'department': u['department'],
                'role': 'employee',
                'is_active': True,
                'is_online': False,
                'risk_score': 0,
                'avatar_color': u['color'],
                'created_at': get_ist_now()
            })

    print('✅ Sample users seeded (john, sarah, mike) → password: password123')

    # -------- MongoDB Indexes --------
    db.users.create_index('username', unique=True)
    db.users.create_index('email', unique=True)
    db.login_attempts.create_index([('user_id', 1), ('timestamp', -1)])
    db.file_accesses.create_index([('user_id', 1), ('timestamp', -1)])
    db.messages.create_index([('sender_id', 1), ('receiver_id', 1)])
    db.messages.create_index([('team_id', 1), ('timestamp', 1)])
    db.notifications.create_index([('user_id', 1), ('timestamp', -1)])
    print('✅ MongoDB indexes created')
