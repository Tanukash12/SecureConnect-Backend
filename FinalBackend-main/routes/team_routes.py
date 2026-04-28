"""
Team Routes
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from config.db import mongo
from utils.auth_middleware import token_required
from utils.helpers import get_ist_now, dt_isoformat
from utils.notifications import create_notification
from extensions import socketio

team_bp = Blueprint('teams', __name__)


def _oid(val):
    try:
        return ObjectId(val)
    except Exception:
        return None


# ==================== GET TEAMS ====================

@team_bp.route('/teams', methods=['GET'])
@token_required
def get_teams(current_user):
    db = mongo.db
    uid = str(current_user['_id'])
    memberships = list(db.team_members.find({'user_id': uid}))

    teams = []
    for m in memberships:
        team = db.teams.find_one({'_id': _oid(m['team_id'])})
        if team:
            count = db.team_members.count_documents({'team_id': str(team['_id'])})
            teams.append({
                'id':           str(team['_id']),
                'name':         team['name'],
                'description':  team.get('description', ''),
                'member_count': count,
                'created_at':   dt_isoformat(team.get('created_at'))
            })

    return jsonify({'teams': teams}), 200


# ==================== CREATE TEAM ====================

@team_bp.route('/teams', methods=['POST'])
@token_required
def create_team(current_user):
    data = request.json or {}
    if not data.get('name'):
        return jsonify({'message': 'Team name is required'}), 400

    db = mongo.db
    uid = str(current_user['_id'])
    now = get_ist_now()

    team = {
        'name':        data['name'],
        'description': data.get('description', ''),
        'created_by':  uid,
        'created_at':  now
    }

    try:
        result = db.teams.insert_one(team)
        team_id = str(result.inserted_id)

        # Add creator as admin
        db.team_members.insert_one({
            'team_id': team_id, 'user_id': uid,
            'role': 'admin', 'joined_at': now
        })

        # Add additional members
        for member_id in data.get('member_ids', []):
            if member_id == uid:
                continue
            u = db.users.find_one({'_id': _oid(member_id)})
            if u:
                db.team_members.insert_one({
                    'team_id': team_id, 'user_id': str(member_id),
                    'role': 'member', 'joined_at': now
                })
                create_notification(db, socketio, str(member_id),
                                    'Added to Team',
                                    f'{current_user["full_name"]} added you to team "{data["name"]}"',
                                    'info')

        count = db.team_members.count_documents({'team_id': team_id})
        return jsonify({
            'message': 'Team created successfully',
            'team': {'id': team_id, 'name': data['name'],
                     'description': data.get('description', ''),
                     'member_count': count}
        }), 201

    except Exception as e:
        return jsonify({'message': 'Failed to create team', 'error': str(e)}), 500


# ==================== GET MEMBERS ====================

@team_bp.route('/teams/<team_id>/members', methods=['GET'])
@token_required
def get_team_members(current_user, team_id):
    db = mongo.db
    uid = str(current_user['_id'])

    if not db.team_members.find_one({'team_id': team_id, 'user_id': uid}):
        return jsonify({'message': 'You are not a member of this team'}), 403

    memberships = list(db.team_members.find({'team_id': team_id}))
    result = []
    for m in memberships:
        u = db.users.find_one({'_id': _oid(m['user_id'])})
        if u:
            result.append({
                'id':          str(u['_id']),
                'username':    u['username'],
                'full_name':   u['full_name'],
                'department':  u.get('department', ''),
                'role':        m['role'],
                'avatar_color': u.get('avatar_color', '#667eea'),
                'is_online':   u.get('is_online', False),
                'joined_at':   dt_isoformat(m.get('joined_at'))
            })

    return jsonify({'members': result}), 200


# ==================== ADD MEMBER ====================

@team_bp.route('/teams/<team_id>/add-member', methods=['POST'])
@token_required
def add_team_member(current_user, team_id):
    data = request.json or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'message': 'User ID is required'}), 400

    db = mongo.db
    uid = str(current_user['_id'])

    if not db.team_members.find_one({'team_id': team_id, 'user_id': uid, 'role': 'admin'}):
        return jsonify({'message': 'Only team admins can add members'}), 403

    if db.team_members.find_one({'team_id': team_id, 'user_id': str(user_id)}):
        return jsonify({'message': 'User is already a member'}), 400

    u = db.users.find_one({'_id': _oid(user_id)})
    if not u:
        return jsonify({'message': 'User not found'}), 404

    db.team_members.insert_one({
        'team_id': team_id, 'user_id': str(user_id),
        'role': 'member', 'joined_at': get_ist_now()
    })

    team = db.teams.find_one({'_id': _oid(team_id)})
    create_notification(db, socketio, str(user_id), 'Added to Team',
                        f'{current_user["full_name"]} added you to team "{team["name"]}"', 'info')

    return jsonify({'message': 'Member added successfully'}), 201


# ==================== REMOVE MEMBER ====================

@team_bp.route('/teams/<team_id>/remove-member', methods=['POST'])
@token_required
def remove_team_member(current_user, team_id):
    data = request.json or {}
    user_id = str(data.get('user_id', ''))
    if not user_id:
        return jsonify({'message': 'User ID is required'}), 400

    db = mongo.db
    uid = str(current_user['_id'])

    if not db.team_members.find_one({'team_id': team_id, 'user_id': uid, 'role': 'admin'}):
        return jsonify({'message': 'Only team admins can remove members'}), 403

    member = db.team_members.find_one({'team_id': team_id, 'user_id': user_id})
    if not member:
        return jsonify({'message': 'Member not found'}), 404

    if member['role'] == 'admin':
        admin_count = db.team_members.count_documents({'team_id': team_id, 'role': 'admin'})
        if admin_count <= 1:
            return jsonify({'message': 'Cannot remove the last admin'}), 400

    db.team_members.delete_one({'_id': member['_id']})
    team = db.teams.find_one({'_id': _oid(team_id)})
    create_notification(db, socketio, user_id, 'Removed from Team',
                        f'You were removed from team "{team["name"]}"', 'warning')

    return jsonify({'message': 'Member removed successfully'}), 200
