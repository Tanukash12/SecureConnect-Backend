import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- Security ---
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("❌ SECRET_KEY environment variable is not set!")

    # --- MongoDB ---
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/enterprise_db')

    # --- JWT ---
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 24))

    # --- Admin seed ---
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

    # --- ML Model ---
    ML_MODEL_PATH = os.environ.get('ML_MODEL_PATH', 'ml/intrusion_model.pkl')
