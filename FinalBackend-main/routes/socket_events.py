"""
Socket.IO Events
"""
import jwt
from flask import current_app
from flask_socketio import emit, join_room, leave_room
from bson import ObjectId
from config.db import mongo
from utils.helpers import get_ist_now
from utils.notifications import create_notification


def register_socket_events(socketio):

    @socketio.on('connect')
    def on_connect():
        print('🔌 Client connected')

    @socketio.on('disconnect')
    def on_disconnect():
        print('🔌 Client disconnected')

    # ---- User Online ----
    @socketio.on('user_online')
    def handle_user_online(data):
        token = data.get('token')
        if not token:
            return
        try:
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user = mongo.db.users.find_one({'_id': ObjectId(decoded['user_id'])})
            if user:
                mongo.db.users.update_one({'_id': user['_id']}, {'$set': {
                    'is_online': True, 'last_seen': get_ist_now()
                }})
                join_room(f'user_{user["_id"]}')
                emit('user_status', {'user_id': str(user['_id']), 'status': 'online'}, broadcast=True)
        except Exception as e:
            print(f'user_online error: {e}')

    # ---- User Offline ----
    @socketio.on('user_offline')
    def handle_user_offline(data):
        token = data.get('token')
        if not token:
            return
        try:
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user = mongo.db.users.find_one({'_id': ObjectId(decoded['user_id'])})
            if user:
                mongo.db.users.update_one({'_id': user['_id']}, {'$set': {
                    'is_online': False, 'last_seen': get_ist_now()
                }})
                leave_room(f'user_{user["_id"]}')
                emit('user_status', {'user_id': str(user['_id']), 'status': 'offline'}, broadcast=True)
        except Exception as e:
            print(f'user_offline error: {e}')

    # ---- Send Message ----
    @socketio.on('send_message')
    def handle_send_message(data):
        try:
            db = mongo.db
            now = get_ist_now()

            msg = {
                'sender_id':    data['sender_id'],
                'receiver_id':  data.get('receiver_id'),
                'team_id':      data.get('team_id'),
                'content':      data['content'],
                'message_type': data.get('type', 'text'),
                'is_read':      False,
                'timestamp':    now
            }
            result = db.messages.insert_one(msg)

            sender = db.users.find_one({'_id': ObjectId(data['sender_id'])})

            msg_data = {
                'id':              str(result.inserted_id),
                'sender_id':       data['sender_id'],
                'sender_name':     sender['full_name']          if sender else 'Unknown',
                'sender_username': sender['username']           if sender else 'unknown',
                'sender_avatar':   sender.get('avatar_color', '#ccc') if sender else '#ccc',
                'receiver_id':     data.get('receiver_id'),
                'team_id':         data.get('team_id'),
                'content':         data['content'],
                'timestamp':       now.isoformat()
            }

            if data.get('receiver_id'):
                emit('new_message', msg_data, room=f'user_{data["receiver_id"]}')
                create_notification(db, socketio,
                                    data['receiver_id'],
                                    f'New message from {sender["full_name"] if sender else "Someone"}',
                                    data['content'][:50], 'message')
            elif data.get('team_id'):
                emit('new_team_message', msg_data,
                     room=f'team_{data["team_id"]}', include_self=True)

        except Exception as e:
            print(f'send_message error: {e}')
            emit('message_error', {'error': str(e)})

    # ---- Team Join/Leave ----
    @socketio.on('join_team')
    def handle_join_team(data):
        join_room(f'team_{data["team_id"]}')
        emit('joined_team', {'team_id': data['team_id']})

    @socketio.on('leave_team')
    def handle_leave_team(data):
        leave_room(f'team_{data["team_id"]}')

    # ---- Typing indicator ----
    @socketio.on('typing')
    def handle_typing(data):
        if data.get('receiver_id'):
            emit('user_typing', {
                'user_id': data['sender_id'],
                'typing':  data['typing']
            }, room=f'user_{data["receiver_id"]}')
