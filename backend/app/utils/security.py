# app/utils/security.py  —  JWT + password hashing (bcrypt direct, no passlib)
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt as _bcrypt
from jose import JWTError, jwt
from config import settings
from app.schemas.auth import TokenData

def hash_password(plain: str) -> str:
    truncated = plain.encode("utf-8")[:72]
    return _bcrypt.hashpw(truncated, _bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    truncated = plain.encode("utf-8")[:72]
    try:
        return _bcrypt.checkpw(truncated, hashed.encode("utf-8"))
    except Exception:
        return False

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def create_access_token(user_id: str, email: str) -> str:
    expire = _utc_now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "email": email, "type": "access", "exp": expire, "iat": _utc_now()}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def create_refresh_token(user_id: str, email: str) -> str:
    expire = _utc_now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": user_id, "email": email, "type": "refresh", "exp": expire, "iat": _utc_now()}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        token_type: str = payload.get("type", "access")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, email=email, token_type=token_type)
    except JWTError:
        return None

def access_token_expire_seconds() -> int:
    return settings.access_token_expire_minutes * 60
