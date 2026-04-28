"""
Auth Routes — /api/register, /api/login
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import jwt
from bson import ObjectId

from config.db import mongo
from utils.helpers import (get_ist_now, get_location_from_ip,
                            detect_suspicious_login, calculate_risk_score)
from utils.notifications import create_notification
from ml.model_loader import predict_intrusion
from extensions import socketio

auth_bp = Blueprint('auth', __name__)


def _user_response(user: dict) -> dict:
    return {
        'id':           str(user['_id']),
        'username':     user['username'],
        'full_name':    user['full_name'],
        'email':        user['email'],
        'role':         user['role'],
        'department':   user.get('department', ''),
        'avatar_color': user.get('avatar_color', '#667eea'),
    }


# ==================== REGISTER ====================

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}

    required = ('username', 'email', 'password', 'full_name')
    if not all(k in data for k in required):
        return jsonify({'message': 'Missing required fields'}), 400

    db = mongo.db
    if db.users.find_one({'username': data['username']}):
        return jsonify({'message': 'Username already exists'}), 400
    if db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already exists'}), 400

    new_user = {
        'username':     data['username'],
        'email':        data['email'],
        'password':     generate_password_hash(data['password']),
        'full_name':    data['full_name'],
        'department':   data.get('department', 'General'),
        'role':         data.get('role', 'employee'),
        'is_active':    True,
        'is_online':    False,
        'risk_score':   0,
        'avatar_color': data.get('avatar_color', '#667eea'),
        'created_at':   get_ist_now(),
        'last_login':   None,
        'last_seen':    None,
    }

    try:
        db.users.insert_one(new_user)
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500


# ==================== LOGIN ====================

@auth_bp.route('/login', methods=['POST'])
def login():
    data   = request.json or {}
    ip     = request.remote_addr or '127.0.0.1'
    device = request.headers.get('User-Agent', 'Unknown')[:200]
    location = get_location_from_ip(ip)
    db     = mongo.db

    user = db.users.find_one({'username': data.get('username', '')})

    # ---- Failed login ----
    if not user or not check_password_hash(user['password'], data.get('password', '')):
        db.login_attempts.insert_one({
            'user_id':    str(user['_id']) if user else None,
            'username':   data.get('username', ''),
            'ip_address': ip,
            'device_info': device,
            'location':   location,
            'status':     'failed',
            'is_suspicious': False,
            'timestamp':  get_ist_now()
        })
        if user:
            new_score = calculate_risk_score(db, user['_id'])
            db.users.update_one({'_id': user['_id']}, {'$set': {'risk_score': new_score}})
        return jsonify({'message': 'Invalid credentials'}), 401

    if not user.get('is_active', True):
        return jsonify({'message': 'Account is suspended'}), 403

    # ---- Suspicious detection ----
    rule_suspicious = detect_suspicious_login(db, user['_id'], ip, device)
    ml_suspicious   = predict_intrusion(
        failed_logins=db.login_attempts.count_documents({
            'user_id': str(user['_id']), 'status': 'failed',
            'timestamp': {'$gte': get_ist_now() - timedelta(hours=1)}
        }),
        risk_score=user.get('risk_score', 0)
    )
    is_suspicious = rule_suspicious or ml_suspicious

    # ---- Record attempt ----
    db.login_attempts.insert_one({
        'user_id':     str(user['_id']),
        'username':    user['username'],
        'ip_address':  ip,
        'device_info': device,
        'location':    location,
        'status':      'suspicious' if is_suspicious else 'success',
        'is_suspicious': is_suspicious,
        'timestamp':   get_ist_now()
    })

    # ---- Update user ----
    new_score = calculate_risk_score(db, user['_id'])
    db.users.update_one({'_id': user['_id']}, {'$set': {
        'last_login':  get_ist_now(),
        'last_seen':   get_ist_now(),
        'is_online':   True,
        'risk_score':  new_score
    }})

    if is_suspicious:
        create_notification(db, socketio, str(user['_id']),
                            'Suspicious Login Detected',
                            f'New login from {location} on {device[:50]}',
                            'warning')

    # ---- JWT ----
    token = jwt.encode({
        'user_id':  str(user['_id']),
        'username': user['username'],
        'role':     user['role'],
        'exp':      get_ist_now() + timedelta(hours=current_app.config['JWT_EXPIRY_HOURS'])
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'token': token,
        'user': {**_user_response(user), 'is_suspicious': is_suspicious}
    }), 200
