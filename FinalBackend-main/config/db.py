from flask_pymongo import PyMongo

mongo = PyMongo()

def init_db(app):
    mongo.init_app(app, uri=app.config['MONGO_URI'])
    print("✅ MongoDB Connected")
    return mongo
