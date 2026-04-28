"""
File Access Routes
"""
from flask import Blueprint, request, jsonify
from config.db import mongo
from utils.auth_middleware import token_required
from utils.helpers import get_ist_now, calculate_risk_score
from utils.notifications import create_notification
from extensions import socketio

file_bp = Blueprint('files', __name__)

RESTRICTED_PATHS = ['/confidential/', '/admin/', '/hr/salary', '/credentials', '/passwords']


@file_bp.route('/file-access', methods=['POST'])
@token_required
def file_access(current_user):
    data      = request.json or {}
    file_path = data.get('file_path', '')
    db        = mongo.db
    uid       = str(current_user['_id'])

    is_authorized = True
    risk_level    = 'low'

    for restricted in RESTRICTED_PATHS:
        if restricted in file_path:
            if current_user.get('role') != 'admin':
                is_authorized = False
                risk_level    = 'critical' if '/admin/' in file_path else 'high'
            break

    db.file_accesses.insert_one({
        'user_id':      uid,
        'username':     current_user['username'],
        'file_path':    file_path,
        'action':       'allowed' if is_authorized else 'denied',
        'risk_level':   risk_level,
        'is_authorized': is_authorized,
        'timestamp':    get_ist_now()
    })

    if not is_authorized:
        new_score = calculate_risk_score(db, current_user['_id'])
        db.users.update_one({'_id': current_user['_id']}, {'$set': {'risk_score': new_score}})
        create_notification(db, socketio, uid,
                            'Unauthorized Access Attempt',
                            f'Access denied to {file_path}', 'danger')

    status = 200 if is_authorized else 403
    return jsonify({
        'allowed':    is_authorized,
        'risk_level': risk_level,
        'message':    'Access granted' if is_authorized else 'Access denied'
    }), status
