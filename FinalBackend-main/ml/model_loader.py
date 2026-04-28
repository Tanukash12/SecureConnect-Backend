"""
ML Intrusion Detection Module
==============================
Model expects 2 features: [failed_logins_last_hour, current_risk_score]
Output: 1 = suspicious, 0 = normal

To train your own model, run: python ml/train_model.py
"""
import joblib
import numpy as np
import os

_model = None

def load_model(model_path: str):
    global _model
    try:
        _model = joblib.load(model_path)
        print(f"✅ ML Intrusion Detection Model Loaded from {model_path}")
    except FileNotFoundError:
        _model = None
        print(f"⚠️  ML Model not found at {model_path}. Run: python ml/train_model.py")
    except Exception as e:
        _model = None
        print(f"⚠️  ML Model load error: {e}")


def predict_intrusion(failed_logins: int, risk_score: int) -> bool:
    """
    Returns True if login is predicted as suspicious.
    Falls back to False if model is not loaded.
    """
    if _model is None:
        return False
    try:
        features = np.array([[failed_logins, risk_score]])
        prediction = _model.predict(features)[0]
        return bool(prediction)
    except Exception as e:
        print(f"ML Prediction Error: {e}")
        return False


def is_model_loaded() -> bool:
    return _model is not None
