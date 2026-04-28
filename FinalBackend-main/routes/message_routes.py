"""
Message Routes
"""
from flask import Blueprint, jsonify
from bson import ObjectId
from config.db import mongo
from utils.auth_middleware import token_required
from utils.helpers import dt_isoformat

message_bp = Blueprint('messages', __name__)


def _oid(val):
    try:
        return ObjectId(val)
    except Exception:
        return None


# ==================== DIRECT MESSAGES ====================

@message_bp.route('/messages/direct/<other_user_id>', methods=['GET'])
@token_required
def get_direct_messages(current_user, other_user_id):
    db  = mongo.db
    me  = str(current_user['_id'])

    messages = list(db.messages.find({
        '$or': [
            {'sender_id': me,           'receiver_id': other_user_id},
            {'sender_id': other_user_id, 'receiver_id': me}
        ]
    }).sort('timestamp', 1))

    # Mark as read
    db.messages.update_many(
        {'sender_id': other_user_id, 'receiver_id': me, 'is_read': False},
        {'$set': {'is_read': True}}
    )

    return jsonify({'messages': [{
        'id':        str(m['_id']),
        'sender_id': m['sender_id'],
        'content':   m['content'],
        'is_read':   m.get('is_read', False),
        'timestamp': dt_isoformat(m.get('timestamp'))
    } for m in messages]}), 200


# ==================== TEAM MESSAGES ====================

@message_bp.route('/messages/team/<team_id>', methods=['GET'])
@token_required
def get_team_messages(current_user, team_id):
    db  = mongo.db
    uid = str(current_user['_id'])

    if not db.team_members.find_one({'team_id': team_id, 'user_id': uid}):
        return jsonify({'message': 'You are not a member of this team'}), 403

    messages = list(db.messages.find({'team_id': team_id}).sort('timestamp', 1))

    result = []
    for m in messages:
        sender = db.users.find_one({'_id': _oid(m['sender_id'])})
        result.append({
            'id':              str(m['_id']),
            'sender_id':       m['sender_id'],
            'sender_name':     sender['full_name']    if sender else 'Unknown',
            'sender_username': sender['username']     if sender else 'unknown',
            'sender_avatar':   sender.get('avatar_color', '#ccc') if sender else '#ccc',
            'content':         m['content'],
            'timestamp':       dt_isoformat(m.get('timestamp'))
        })

    return jsonify({'messages': result}), 200


# ==================== CONVERSATIONS LIST ====================

@message_bp.route('/messages/conversations', methods=['GET'])
@token_required
def get_conversations(current_user):
    db  = mongo.db
    me  = str(current_user['_id'])

    sent_to    = db.messages.distinct('receiver_id', {'sender_id': me, 'receiver_id': {'$ne': None}})
    recv_from  = db.messages.distinct('sender_id',   {'receiver_id': me})
    user_ids   = set(sent_to) | set(recv_from)

    conversations = []
    for uid in user_ids:
        u = db.users.find_one({'_id': _oid(uid)})
        if not u:
            continue

        last_msg = db.messages.find_one(
            {'$or': [
                {'sender_id': me,  'receiver_id': uid},
                {'sender_id': uid, 'receiver_id': me}
            ]},
            sort=[('timestamp', -1)]
        )

        unread = db.messages.count_documents({
            'sender_id': uid, 'receiver_id': me, 'is_read': False
        })

        conversations.append({
            'user': {
                'id':           str(u['_id']),
                'username':     u['username'],
                'full_name':    u['full_name'],
                'avatar_color': u.get('avatar_color', '#667eea'),
                'is_online':    u.get('is_online', False)
            },
            'last_message': {
                'content':   last_msg['content']                      if last_msg else '',
                'timestamp': dt_isoformat(last_msg.get('timestamp')) if last_msg else None
            },
            'unread_count': unread
        })

    conversations.sort(key=lambda x: x['last_message']['timestamp'] or '', reverse=True)
    return jsonify({'conversations': conversations}), 200
