from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.tables import User, PasswordResetRequestLog
from app.services.emailer import send_email


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_public_token() -> str:
    return secrets.token_urlsafe(32)


def issue_email_verification(db: Session, user: User) -> str:
    token = make_public_token()
    user.email_verification_token_hash = token_hash(token)
    user.email_verification_sent_at = datetime.now(timezone.utc)
    db.add(user); db.commit()
    verify_url = f"{settings.frontend_base_url.rstrip('/')}/api/auth/verify-email?token={token}"
    send_email(
        user.email,
        "Verify your Mogul Grant System email",
        f"Welcome to Mogul Grant System. Verify your email: {verify_url}",
        f"<p>Welcome to <strong>Mogul Grant System</strong>.</p><p><a href='{verify_url}'>Verify your email</a></p>",
    )
    return token


def issue_password_reset(db: Session, user: User | None, email: str, ip_address: str | None = None) -> str | None:
    db.add(PasswordResetRequestLog(tenant_id=getattr(user, 'tenant_id', None), user_id=getattr(user, 'id', None), email=email.lower(), ip_address=ip_address))
    if not user:
        db.commit()
        return None
    token = make_public_token()
    user.password_reset_token_hash = token_hash(token)
    user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=45)
    db.add(user); db.commit()
    reset_url = f"{settings.frontend_base_url.rstrip('/')}/signup.html?mode=reset&token={token}"
    send_email(
        user.email,
        "Reset your Mogul Grant System password",
        f"Reset your Mogul Grant System password here: {reset_url}. This link expires in 45 minutes.",
        f"<p>Reset your Mogul Grant System password:</p><p><a href='{reset_url}'>Reset password</a></p><p>This link expires in 45 minutes.</p>",
    )
    return token
