
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.tables import Subscription, UsageEvent, User

# Plan limits are enforced server-side. Frontend hiding is only UX.
# Credits are monthly and deducted in addition to feature-specific quotas.
PLAN_LIMITS = {
    # Public-facing paid plans. Old plan IDs are normalized below for backward compatibility.
    "individual_elite": {
        "price": "$99/mo",
        "credits": 999999,
        "grant_searches": 999999,
        "proposals": 999999,
        "workflows": 999999,
        "documents": 999999,
        "pdf_exports": 999999,
        "private_grants": True,
        "white_label": False,
        "team_members": 1,
        "admin_access": False,
        "fair_use": True,
        "audience": "individuals",
    },
    "business_owner": {
        "price": "$299/mo",
        "credits": 999999,
        "grant_searches": 999999,
        "proposals": 999999,
        "workflows": 999999,
        "documents": 999999,
        "pdf_exports": 999999,
        "private_grants": True,
        "white_label": False,
        "team_members": 5,
        "admin_access": False,
        "fair_use": True,
        "audience": "businesses",
    },
    "white_label_platform": {
        "price": "$5,000+/yr",
        "credits": 999999,
        "grant_searches": 999999,
        "proposals": 999999,
        "workflows": 999999,
        "documents": 999999,
        "pdf_exports": 999999,
        "private_grants": True,
        "white_label": True,
        "team_members": 999999,
        "admin_access": True,
        "fair_use": True,
        "audience": "agencies",
    },
}

PLAN_ALIASES = {
    "individual": "individual_elite",
    "individual_starter": "individual_elite",
    "individual_pro": "individual_elite",
    "business": "business_owner",
    "business_growth": "business_owner",
    "business_scale": "business_owner",
    "business_enterprise": "business_owner",
    "white_label": "white_label_platform",
    "white_label_agency": "white_label_platform",
    "white_label_studio": "white_label_platform",
}

def normalize_plan(plan: str | None) -> str:
    return PLAN_ALIASES.get((plan or "").strip(), (plan or "individual_elite").strip())

PLAN_LABELS = {
    "individual_elite": "Individual Elite",
    "business_owner": "Business Owner",
    "white_label_platform": "White Label Platform",
}

EVENT_TO_LIMIT = {
    "grant_search": "grant_searches",
    "proposal_generate": "proposals",
    "workflow_run": "workflows",
    "document_upload": "documents",
    "pdf_export": "pdf_exports",
}

EVENT_CREDIT_COST = {
    "grant_search": 1,
    "proposal_generate": 5,
    "workflow_run": 10,
    "document_upload": 2,
    "pdf_export": 1,
}

PRIVATE_GRANT_CATEGORIES = {"private", "corporate"}

def current_plan(db: Session, user: User) -> str:
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.id.desc()).first()
    if sub and sub.plan:
        return normalize_plan(sub.plan)
    return normalize_plan(getattr(user.tenant, "plan", None) or "individual_elite")

def plan_limits(db: Session, user: User) -> dict:
    plan = current_plan(db, user)
    data = PLAN_LIMITS.get(plan, PLAN_LIMITS["individual_elite"]).copy()
    data["plan"] = plan
    data["label"] = PLAN_LABELS.get(plan, plan.replace("_", " ").title())
    return data

def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)

def _monthly_quantity(db: Session, user: User, event_type: str) -> int:
    month_start = _month_start()
    total = db.query(func.coalesce(func.sum(UsageEvent.quantity), 0)).filter(
        UsageEvent.user_id == user.id,
        UsageEvent.event_type == event_type,
        UsageEvent.created_at >= month_start,
    ).scalar()
    return int(total or 0)

def _monthly_credit_adjustment(db: Session, user: User) -> int:
    return _monthly_quantity(db, user, "credit_adjustment")

def _monthly_credits_used(db: Session, user: User) -> int:
    total = 0
    for event_type, cost in EVENT_CREDIT_COST.items():
        total += _monthly_quantity(db, user, event_type) * int(cost)
    return max(0, total - _monthly_credit_adjustment(db, user))

def usage_summary(db: Session, user: User) -> dict:
    limits = plan_limits(db, user)
    used = {}
    for event_type, limit_key in EVENT_TO_LIMIT.items():
        used[limit_key] = _monthly_quantity(db, user, event_type)
    credits_total = int(limits.get("credits", 0))
    credits_used = _monthly_credits_used(db, user)
    credits_remaining = max(0, credits_total - credits_used) if credits_total < 999999 else 999999
    return {
        "plan": limits["plan"],
        "label": limits.get("label"),
        "limits": limits,
        "used": used,
        "credits": {
            "total": credits_total,
            "used": credits_used,
            "remaining": credits_remaining,
            "reset_date": _month_start().replace(month=(_month_start().month % 12) + 1, year=_month_start().year + (1 if _month_start().month == 12 else 0)).date().isoformat(),
            "costs": EVENT_CREDIT_COST,
        }
    }

def require_credits(db: Session, user: User, event_type: str, quantity: int = 1) -> None:
    from fastapi import HTTPException
    cost = int(EVENT_CREDIT_COST.get(event_type, 0)) * max(1, int(quantity))
    if cost <= 0:
        return
    limits = plan_limits(db, user)
    credits_total = int(limits.get("credits", 0))
    if credits_total >= 999999:
        return
    remaining = max(0, credits_total - _monthly_credits_used(db, user))
    if remaining < cost:
        raise HTTPException(status_code=403, detail=f"Not enough credits. This action costs {cost} credits and you have {remaining} remaining. Please upgrade or ask an admin to add credits.")

def check_and_record_usage(db: Session, user: User, event_type: str, metadata: dict | None = None, quantity: int = 1) -> None:
    from fastapi import HTTPException
    qty = max(1, int(quantity))
    limits = plan_limits(db, user)
    limit_key = EVENT_TO_LIMIT.get(event_type)
    if not limit_key:
        return
    limit = int(limits.get(limit_key, 0))
    used = _monthly_quantity(db, user, event_type)
    if limit < 999999 and used + qty > limit:
        raise HTTPException(status_code=403, detail=f"Plan limit reached for {limit_key}. Upgrade your plan to continue.")
    require_credits(db, user, event_type, qty)
    db.add(UsageEvent(tenant_id=user.tenant_id, user_id=user.id, event_type=event_type, quantity=qty, metadata_json=metadata or {}))
    db.commit()

def add_credits(db: Session, admin: User, target: User, credits: int, reason: str = "admin_credit_adjustment") -> dict:
    credits = int(credits)
    if credits <= 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="credits must be greater than zero")
    db.add(UsageEvent(tenant_id=target.tenant_id, user_id=target.id, event_type="credit_adjustment", quantity=credits, metadata_json={"reason": reason, "admin_user_id": admin.id}))
    db.commit()
    return usage_summary(db, target)

def plan_matrix() -> list[dict]:
    rows = []
    for plan, data in PLAN_LIMITS.items():
        row = data.copy()
        row["plan"] = plan
        row["label"] = PLAN_LABELS.get(plan, plan)
        rows.append(row)
    return rows

def is_private_grant_category(category: str | None) -> bool:
    return (category or "").strip().lower() in PRIVATE_GRANT_CATEGORIES

def feature_map(db: Session, user: User, preview_plan: str | None = None) -> dict:
    preview_plan = normalize_plan(preview_plan) if preview_plan else None
    if preview_plan and preview_plan in PLAN_LIMITS and user.role in {"owner", "admin"}:
        limits = PLAN_LIMITS[preview_plan].copy()
        limits["plan"] = preview_plan
    else:
        limits = plan_limits(db, user)
    plan = limits.get("plan", "individual_elite")
    admin_allowed = user.role in {"owner", "admin"} and bool(limits.get("admin_access", False))
    return {
        "grant_search": int(limits.get("grant_searches", 0)) > 0,
        "proposals": int(limits.get("proposals", 0)) > 0,
        "workflows": int(limits.get("workflows", 0)) > 0,
        "documents": int(limits.get("documents", 0)) > 0,
        "pdf_exports": int(limits.get("pdf_exports", 0)) > 0,
        "private_grants": bool(limits.get("private_grants", False)),
        "white_label": bool(limits.get("white_label", False)) and user.role in {"owner", "admin"},
        "admin": admin_allowed,
        "notifications": True,
        "tracker": True,
        "profiles": True,
        "client_profile": True,
        "plan": plan,
        "preview": bool(preview_plan),
    }

def require_feature(db: Session, user: User, feature: str) -> None:
    from fastapi import HTTPException
    features = feature_map(db, user)
    if not features.get(feature, False):
        pretty = feature.replace("_", " ").title()
        raise HTTPException(status_code=403, detail=f"{pretty} is not included in your current plan. Please upgrade to continue.")

def user_can_white_label(db: Session, user: User) -> bool:
    if user.role in {"owner", "admin"}:
        return bool(plan_limits(db, user).get("white_label")) or current_plan(db, user).startswith("white_label_")
    return False
