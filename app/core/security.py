from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import os
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db

# Password hashing uses PBKDF2-SHA256 and supports long passwords.
# Format: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
PBKDF2_ITERATIONS = 390000
bearer = HTTPBearer(auto_error=False)

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def hash_password(password: str) -> str:
    if not isinstance(password, str) or password == "":
        raise ValueError("Password cannot be empty")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = _unb64(salt_b64)
        expected = _unb64(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        # Never let malformed/old hashes create 500 errors during login.
        return False

def create_token(subject: str, token_type: str = "access", minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    if token_type == "refresh":
        exp = now + timedelta(days=settings.refresh_token_days)
    else:
        exp = now + timedelta(minutes=minutes or settings.access_token_minutes)
    payload = {"sub": subject, "type": token_type, "iat": int(now.timestamp()), "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    from app.models.tables import User
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    payload = decode_token(creds.credentials)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(user = Depends(current_user)):
    if user.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def require_paid_user(user = Depends(current_user), db: Session = Depends(get_db)):
    """Gate premium endpoints.

    While PAYMENT_REQUIRED=false, every registered user can use the platform.
    Turn PAYMENT_REQUIRED=true later when your Stripe account is ready.
    """
    if not settings.payment_required:
        return user
    from app.models.tables import Subscription
    active_statuses = {"active", "trialing"}
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.id.desc()).first()
    if not user.is_active or user.payment_status not in active_statuses or not sub or sub.status not in active_statuses:
        raise HTTPException(status_code=402, detail="Payment required. Please complete your monthly subscription before using Mogul Grant System.")
    return user
