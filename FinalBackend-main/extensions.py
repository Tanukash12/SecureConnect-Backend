from flask_socketio import SocketIO

# Global SocketIO instance
# Saari routes yahan se import karein - no circular import
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
