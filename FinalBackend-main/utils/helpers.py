"""
Shared utility functions
"""
import pytz
import requests
from datetime import datetime, timedelta
from bson import ObjectId

IST = pytz.timezone('Asia/Kolkata')


# ==================== TIMEZONE ====================

def get_ist_now() -> datetime:
    """Current datetime in IST (timezone-aware)."""
    return datetime.now(IST)


def utc_to_ist(utc_dt: datetime):
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(IST)


def dt_isoformat(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


# ==================== IP / LOCATION ====================

def get_location_from_ip(ip: str) -> str:
    try:
        if ip in ('127.0.0.1', 'localhost', '::1'):
            return 'Local Network'
        resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
        data = resp.json()
        return f"{data.get('city', 'Unknown')}, {data.get('country', 'Unknown')}"
    except Exception:
        return 'Unknown'


# ==================== RISK SCORE ====================

def calculate_risk_score(db, user_id) -> int:
    """Calculate user risk score from MongoDB login/file data."""
    one_hour_ago = get_ist_now() - timedelta(hours=1)
    uid_str = str(user_id)

    failed_logins = db.login_attempts.count_documents({
        'user_id': uid_str,
        'status': 'failed',
        'timestamp': {'$gte': one_hour_ago}
    })

    unauthorized = db.file_accesses.count_documents({
        'user_id': uid_str,
        'is_authorized': False,
        'timestamp': {'$gte': one_hour_ago}
    })

    suspicious = db.login_attempts.count_documents({
        'user_id': uid_str,
        'is_suspicious': True,
        'timestamp': {'$gte': one_hour_ago}
    })

    score = (failed_logins * 10) + (unauthorized * 25) + (suspicious * 15)
    return min(score, 100)


# ==================== SUSPICIOUS LOGIN ====================

def detect_suspicious_login(db, user_id, ip: str, device: str) -> bool:
    recent = list(db.login_attempts.find(
        {'user_id': str(user_id), 'status': {'$in': ['success', 'suspicious']}},
        sort=[('timestamp', -1)],
        limit=5
    ))
    if not recent:
        return False
    known_ips = {r['ip_address'] for r in recent}
    known_devices = {r['device_info'] for r in recent}
    return ip not in known_ips or device not in known_devices


# ==================== SERIALIZER ====================

def serialize_id(doc: dict) -> dict:
    """Convert MongoDB _id ObjectId to string 'id' field."""
    if doc and '_id' in doc:
        doc['id'] = str(doc['_id'])
        del doc['_id']
    return doc
