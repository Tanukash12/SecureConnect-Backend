from flask import Flask
from flask_cors import CORS
from config.db import init_db
from config.settings import Config
from extensions import socketio
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS
    # CORS(app, resources={r"/api/*": {"origins": os.environ.get("FRONTEND_URL", "*")}})
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Init MongoDB
    init_db(app)

    # Init SocketIO (threading - works on Python 3.14)
    socketio.init_app(app, async_mode='threading')

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.team_routes import team_bp
    from routes.message_routes import message_bp
    from routes.notification_routes import notif_bp
    from routes.admin_routes import admin_bp
    from routes.file_routes import file_bp
    from routes.socket_events import register_socket_events

    app.register_blueprint(auth_bp,         url_prefix='/api')
    app.register_blueprint(user_bp,         url_prefix='/api')
    app.register_blueprint(team_bp,         url_prefix='/api')
    app.register_blueprint(message_bp,      url_prefix='/api')
    app.register_blueprint(notif_bp,        url_prefix='/api')
    app.register_blueprint(admin_bp,        url_prefix='/api/admin')
    app.register_blueprint(file_bp,         url_prefix='/api')

    register_socket_events(socketio)

    @app.route('/')
    def home():
        return {"message": "Enterprise Platform API Running ✅", "status": "ok"}

    return app


app = create_app()

if __name__ == '__main__':
    from utils.seed import seed_users
    with app.app_context():
        seed_users()
    socketio.run(app, debug=False, host='0.0.0.0',
                 port=int(os.environ.get('PORT', 5000)),
                 allow_unsafe_werkzeug=True)
