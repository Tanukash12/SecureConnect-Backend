"""
User Routes — /api/users, /api/profile
"""
from flask import Blueprint, jsonify
from config.db import mongo
from utils.auth_middleware import token_required
from utils.helpers import dt_isoformat

user_bp = Blueprint('users', __name__)


def _fmt_user(u, include_private=False):
    d = {
        'id':           str(u['_id']),
        'username':     u['username'],
        'full_name':    u['full_name'],
        'email':        u['email'],
        'department':   u.get('department', ''),
        'role':         u.get('role', 'employee'),
        'is_online':    u.get('is_online', False),
        'last_seen':    dt_isoformat(u.get('last_seen')),
        'avatar_color': u.get('avatar_color', '#667eea'),
    }
    if include_private:
        d['risk_score'] = u.get('risk_score', 0)
    return d


@user_bp.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    users = list(mongo.db.users.find({'_id': {'$ne': current_user['_id']}}))
    return jsonify({'users': [_fmt_user(u) for u in users]}), 200


@user_bp.route('/users/online', methods=['GET'])
@token_required
def get_online_users(current_user):
    users = list(mongo.db.users.find({
        'is_online': True,
        '_id': {'$ne': current_user['_id']}
    }))
    return jsonify({'users': [_fmt_user(u) for u in users]}), 200


@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify(_fmt_user(current_user, include_private=True)), 200
