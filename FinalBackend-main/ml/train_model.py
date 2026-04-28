"""
Train Intrusion Detection Model
================================
Run this script once to generate intrusion_model.pkl

Usage:
    python ml/train_model.py

Features used:
    - failed_logins_last_hour  : number of failed logins in last hour
    - current_risk_score       : user's current risk score (0-100)

Label:
    - 0 = Normal login
    - 1 = Suspicious / Intrusion
"""

import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ==================== SYNTHETIC TRAINING DATA ====================
# Format: [failed_logins_last_hour, risk_score]
# In production: replace with real logs from your MongoDB

np.random.seed(42)

# Normal logins (label = 0)
normal_data = np.column_stack([
    np.random.randint(0, 2, 500),     # 0-1 failed logins
    np.random.randint(0, 20, 500),    # low risk score
])

# Suspicious logins (label = 1)
suspicious_data = np.column_stack([
    np.random.randint(3, 15, 200),    # 3+ failed logins
    np.random.randint(40, 100, 200),  # high risk score
])

# Edge cases - medium risk
medium_data = np.column_stack([
    np.random.randint(1, 4, 100),
    np.random.randint(20, 50, 100),
])
medium_labels = np.random.choice([0, 1], size=100, p=[0.6, 0.4])

X = np.vstack([normal_data, suspicious_data, medium_data])
y = np.concatenate([
    np.zeros(500),   # normal
    np.ones(200),    # suspicious
    medium_labels    # mixed
])

# ==================== TRAIN ====================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=5,
    random_state=42,
    class_weight='balanced'
)
model.fit(X_train, y_train)

# ==================== EVALUATE ====================
y_pred = model.predict(X_test)
print("\n📊 Model Evaluation:")
print(classification_report(y_test, y_pred, target_names=['Normal', 'Suspicious']))

# ==================== SAVE ====================
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'intrusion_model.pkl')
joblib.dump(model, save_path)
print(f"\n✅ Model saved to: {save_path}")
print("   You can now start your Flask server.")
