from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_token, current_user, decode_token
from app.models.tables import Tenant, User, Subscription, LoginAttempt
from app.schemas.api import RegisterRequest, LoginRequest, TokenResponse, RegisterCheckoutResponse, ResendVerificationRequest, PasswordResetRequest, PasswordResetConfirm
from app.services.serialize import model_to_dict
from app.api.billing import create_checkout_session_for_user
from app.core.config import settings
from app.services.plans import usage_summary, feature_map, current_plan

from datetime import datetime, timedelta, timezone
import re
from uuid import uuid4
from app.services.auth_tokens import issue_email_verification, issue_password_reset, token_hash

router = APIRouter(prefix="/auth", tags=["Auth"])


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (value or "workspace").lower()).strip("-")
    return base[:40] or "workspace"

def _unique_tenant_slug(db: Session, seed: str) -> str:
    base = _slugify(seed)
    slug = base
    if slug == "default":
        slug = f"{base}-{uuid4().hex[:6]}"
    while db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{base}-{uuid4().hex[:6]}"
    return slug

@router.post("/register", response_model=RegisterCheckoutResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Each new signup gets its own workspace by default.
    # This prevents account switching bugs where different test users share the same
    # tenant/data/plan just because the frontend sent tenant_slug="default".
    requested_slug = (payload.tenant_slug or "default").strip().lower()
    if requested_slug in {"", "default", "grant-simone", "grantsimone"}:
        seed = payload.tenant_name or payload.email.split("@")[0]
        tenant_slug = _unique_tenant_slug(db, seed)
        tenant = Tenant(name=payload.tenant_name or "Mogul Grant Workspace", slug=tenant_slug)
        db.add(tenant); db.commit(); db.refresh(tenant)
    else:
        tenant = db.query(Tenant).filter(Tenant.slug == requested_slug).first()
        if not tenant:
            tenant = Tenant(name=payload.tenant_name, slug=requested_slug)
            db.add(tenant); db.commit(); db.refresh(tenant)
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(409, "Email already exists. Please log in instead.")
    role = "owner" if not tenant.users else "member"
    user = User(
        tenant_id=tenant.id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=role,
        account_type=payload.account_type,
        is_active=not settings.payment_required,
        payment_status="trialing" if not settings.payment_required else "pending_payment",
        email_verified=not settings.email_verification_required,
    )
    db.add(user); db.commit(); db.refresh(user)
    verification_token = None
    if settings.email_verification_required:
        verification_token = issue_email_verification(db, user)
    selected_plan = payload.plan or "individual_elite"

    if not settings.payment_required:
        sub = Subscription(
            tenant_id=user.tenant_id,
            user_id=user.id,
            plan=selected_plan,
            status="trialing",
        )
        db.add(sub); db.commit()
        return RegisterCheckoutResponse(
            access_token=create_token(str(user.id)),
            refresh_token=create_token(str(user.id), "refresh"),
            checkout_url=None,
            payment_required=False,
            plan=selected_plan,
        )

    checkout = create_checkout_session_for_user(db, user, selected_plan)
    return RegisterCheckoutResponse(
        access_token=create_token(str(user.id)),
        refresh_token=create_token(str(user.id), "refresh"),
        checkout_url=checkout["checkout_url"],
        payment_required=True,
        plan=selected_plan,
    )

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Login by email first so users can switch between separately-created
    # workspaces/accounts without remembering an internal tenant slug.
    requested_slug = (payload.tenant_slug or "default").strip().lower()
    tenant = None
    user = None
    if requested_slug not in {"", "default"}:
        tenant = db.query(Tenant).filter(Tenant.slug == requested_slug).first()
        user = db.query(User).filter(User.tenant_id == tenant.id, User.email == payload.email.lower()).first() if tenant else None
    if not user:
        user = db.query(User).filter(User.email == payload.email.lower()).order_by(User.id.desc()).first()
        tenant = user.tenant if user else tenant
    ip = request.client.host if request.client else None
    if user and user.locked_until and user.locked_until > datetime.now(timezone.utc):
        db.add(LoginAttempt(tenant_id=user.tenant_id, user_id=user.id, email=payload.email.lower(), success=False, ip_address=ip, user_agent=request.headers.get("user-agent")))
        db.commit()
        raise HTTPException(423, "Account temporarily locked after repeated failed login attempts. Try again later or reset password.")
    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.max_login_attempts:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_minutes)
            db.add(user)
        db.add(LoginAttempt(tenant_id=getattr(tenant, 'id', None), user_id=getattr(user, 'id', None), email=payload.email.lower(), success=False, ip_address=ip, user_agent=request.headers.get("user-agent")))
        db.commit()
        raise HTTPException(401, "Invalid login")
    if settings.email_verification_required and not user.email_verified:
        raise HTTPException(403, "Please verify your email before logging in.")
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.add(LoginAttempt(tenant_id=user.tenant_id, user_id=user.id, email=user.email, success=True, ip_address=ip, user_agent=request.headers.get("user-agent")))
    db.commit()
    return TokenResponse(access_token=create_token(str(user.id)), refresh_token=create_token(str(user.id), "refresh"))

@router.get("/me")
def me(user = Depends(current_user), db: Session = Depends(get_db)):
    data = model_to_dict(user, exclude={"password_hash"})
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.id.desc()).first()
    data["subscription"] = model_to_dict(sub) if sub else None
    data["has_paid_access"] = True if not settings.payment_required else bool(user.is_active and user.payment_status in {"active", "trialing"} and sub and sub.status in {"active", "trialing"})
    data["payment_required"] = settings.payment_required
    data["usage"] = usage_summary(db, user)
    data["features"] = feature_map(db, user)
    data["plan"] = current_plan(db, user)
    data["can_admin"] = data["features"].get("admin", False)
    data["can_white_label"] = data["features"].get("white_label", False)
    return data


@router.get("/client-profile")
def client_profile(user = Depends(current_user), db: Session = Depends(get_db)):
    from app.models.tables import Organization, Document, Proposal, Application, Subscription
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.id.desc()).first()
    profiles = db.query(Organization).filter(Organization.tenant_id == user.tenant_id).order_by(Organization.created_at.desc()).all()
    return {
        "user": model_to_dict(user, exclude={"password_hash", "email_verification_token_hash", "password_reset_token_hash"}),
        "tenant": model_to_dict(user.tenant),
        "subscription": model_to_dict(sub) if sub else None,
        "plan": current_plan(db, user),
        "features": feature_map(db, user),
        "usage": usage_summary(db, user),
        "counts": {
            "profiles": len(profiles),
            "documents": db.query(Document).filter(Document.tenant_id == user.tenant_id).count(),
            "proposals": db.query(Proposal).filter(Proposal.tenant_id == user.tenant_id).count(),
            "applications": db.query(Application).filter(Application.tenant_id == user.tenant_id).count(),
        },
        "profiles": [model_to_dict(p) for p in profiles],
    }

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    hashed = token_hash(token)
    user = db.query(User).filter(User.email_verification_token_hash == hashed).first()
    if not user:
        raise HTTPException(400, "Invalid or expired verification link")
    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_sent_at = None
    user.is_active = True if not settings.payment_required else user.is_active
    db.add(user); db.commit()
    return {"ok": True, "message": "Email verified. You can now log in."}

@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.slug == payload.tenant_slug).first()
    user = db.query(User).filter(User.tenant_id == tenant.id, User.email == payload.email.lower()).first() if tenant else None
    if user and not user.email_verified:
        token = issue_email_verification(db, user)
        return {"ok": True, "message": "Verification email sent.", "dev_token": token if settings.app_env != "production" else None}
    return {"ok": True, "message": "If the email exists, a verification email will be sent."}

@router.post("/request-password-reset")
def request_password_reset(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.slug == payload.tenant_slug).first()
    user = db.query(User).filter(User.tenant_id == tenant.id, User.email == payload.email.lower()).first() if tenant else None
    token = issue_password_reset(db, user, payload.email, request.client.host if request.client else None)
    return {"ok": True, "message": "If the email exists, a reset link will be sent.", "dev_token": token if token and settings.app_env != "production" else None}

@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    hashed = token_hash(payload.token)
    user = db.query(User).filter(User.password_reset_token_hash == hashed).first()
    if not user or not user.password_reset_expires_at or user.password_reset_expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired password reset link")
    user.password_hash = hash_password(payload.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user); db.commit()
    return {"ok": True, "message": "Password reset successful. You can now log in."}

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    return TokenResponse(access_token=create_token(str(payload["sub"])), refresh_token=create_token(str(payload["sub"]), "refresh"))
