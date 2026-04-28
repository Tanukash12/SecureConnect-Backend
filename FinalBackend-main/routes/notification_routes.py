"""
Notification Routes
"""
from flask import Blueprint, jsonify
from bson import ObjectId
from config.db import mongo
from utils.auth_middleware import token_required
from utils.helpers import dt_isoformat

notif_bp = Blueprint('notifications', __name__)


@notif_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    uid = str(current_user['_id'])
    notifs = list(mongo.db.notifications.find(
        {'user_id': uid}
    ).sort('timestamp', -1).limit(50))

    return jsonify({'notifications': [{
        'id':        str(n['_id']),
        'title':     n['title'],
        'message':   n['message'],
        'type':      n['type'],
        'is_read':   n.get('is_read', False),
        'link':      n.get('link'),
        'timestamp': dt_isoformat(n.get('timestamp'))
    } for n in notifs]}), 200


@notif_bp.route('/notifications/<notif_id>/read', methods=['POST'])
@token_required
def mark_notification_read(current_user, notif_id):
    uid  = str(current_user['_id'])
    notif = mongo.db.notifications.find_one({'_id': ObjectId(notif_id)})

    if notif and notif.get('user_id') == uid:
        mongo.db.notifications.update_one(
            {'_id': ObjectId(notif_id)},
            {'$set': {'is_read': True}}
        )
        return jsonify({'message': 'Notification marked as read'}), 200

    return jsonify({'message': 'Notification not found'}), 404
