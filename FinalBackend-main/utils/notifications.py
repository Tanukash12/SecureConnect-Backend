"""
Notification helper — creates DB record + emits socket event
"""
from utils.helpers import get_ist_now


def create_notification(db, socketio, user_id: str, title: str, message: str,
                        notif_type: str = 'info', link: str = None):
    notif = {
        'user_id': str(user_id),
        'title': title,
        'message': message,
        'type': notif_type,
        'is_read': False,
        'link': link,
        'timestamp': get_ist_now()
    }
    result = db.notifications.insert_one(notif)

    # Real-time push via SocketIO
    socketio.emit('new_notification', {
        'id': str(result.inserted_id),
        'title': title,
        'message': message,
        'type': notif_type,
        'timestamp': notif['timestamp'].isoformat()
    }, room=f'user_{user_id}')
