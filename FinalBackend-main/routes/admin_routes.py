"""
Admin Routes — /api/admin/*
"""
from flask import Blueprint, jsonify
from bson import ObjectId
from config.db import mongo
from utils.auth_middleware import token_required, admin_required
from utils.helpers import get_ist_now, dt_isoformat
from utils.notifications import create_notification
from extensions import socketio
from datetime import datetime, timezone

admin_bp = Blueprint('admin', __name__)


def _today_start():
    now = get_ist_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


# ==================== DASHBOARD ====================

@admin_bp.route('/dashboard', methods=['GET'])
@token_required
@admin_required
def admin_dashboard(current_user):
    db    = mongo.db
    today = _today_start()

    return jsonify({'stats': {
        'total_users':   db.users.count_documents({}),
        'active_users':  db.users.count_documents({'is_active': True}),
        'online_users':  db.users.count_documents({'is_online': True}),
        'today_logins':  db.login_attempts.count_documents({'timestamp': {'$gte': today}}),
        'failed_logins': db.login_attempts.count_documents({'status': 'failed', 'timestamp': {'$gte': today}}),
        'blocked_files': db.file_accesses.count_documents({'is_authorized': False, 'timestamp': {'$gte': today}}),
        'risk_users':    db.users.count_documents({'risk_score': {'$gt': 50}})
    }}), 200


# ==================== LOGIN ATTEMPTS ====================

@admin_bp.route('/login-attempts', methods=['GET'])
@token_required
@admin_required
def get_login_attempts(current_user):
    attempts = list(mongo.db.login_attempts.find().sort('timestamp', -1).limit(100))
    return jsonify({'attempts': [{
        'id':           str(a['_id']),
        'username':     a.get('username', ''),
        'ip_address':   a.get('ip_address', ''),
        'device_info':  a.get('device_info', ''),
        'location':     a.get('location', ''),
        'status':       a.get('status', ''),
        'is_suspicious': a.get('is_suspicious', False),
        'timestamp':    dt_isoformat(a.get('timestamp'))
    } for a in attempts]}), 200


# ==================== FILE ACCESS ====================

@admin_bp.route('/file-access', methods=['GET'])
@token_required
@admin_required
def get_file_access(current_user):
    accesses = list(mongo.db.file_accesses.find().sort('timestamp', -1).limit(100))
    return jsonify({'accesses': [{
        'id':           str(a['_id']),
        'username':     a.get('username', ''),
        'file_path':    a.get('file_path', ''),
        'action':       a.get('action', ''),
        'risk_level':   a.get('risk_level', ''),
        'is_authorized': a.get('is_authorized', True),
        'timestamp':    dt_isoformat(a.get('timestamp'))
    } for a in accesses]}), 200


# ==================== RISK USERS ====================

@admin_bp.route('/risk-users', methods=['GET'])
@token_required
@admin_required
def get_risk_users(current_user):
    db    = mongo.db
    users = list(db.users.find({'risk_score': {'$gt': 0}}).sort('risk_score', -1))

    result = []
    for u in users:
        uid = str(u['_id'])
        failed = db.login_attempts.count_documents({'user_id': uid, 'status': 'failed'})
        unauth = db.file_accesses.count_documents({'user_id': uid, 'is_authorized': False})

        reasons = []
        if failed > 0: reasons.append(f'{failed} failed login(s)')
        if unauth > 0: reasons.append(f'{unauth} unauthorized file access(es)')

        score  = u.get('risk_score', 0)
        status = 'critical' if score > 75 else 'high' if score > 50 else 'medium'

        result.append({
            'id':         uid,
            'username':   u['username'],
            'email':      u['email'],
            'risk_score': score,
            'status':     status,
            'reasons':    ', '.join(reasons),
            'last_login': dt_isoformat(u.get('last_login'))
        })

    return jsonify({'risk_users': result}), 200


# ==================== SUSPEND USER ====================

@admin_bp.route('/user/<user_id>/suspend', methods=['POST'])
@token_required
@admin_required
def suspend_user(current_user, user_id):
    db = mongo.db
    u  = db.users.find_one({'_id': ObjectId(user_id)})
    if not u:
        return jsonify({'message': 'User not found'}), 404

    db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'is_active': False}})
    create_notification(db, socketio, user_id,
                        'Account Suspended',
                        'Your account has been suspended by the administrator',
                        'danger')

    return jsonify({'message': f'User {u["username"]} suspended'}), 200
