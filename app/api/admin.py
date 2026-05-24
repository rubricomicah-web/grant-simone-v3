from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin
from app.services.plans import usage_summary, feature_map, plan_matrix, add_credits
from app.models.tables import Tenant, User, Grant, Proposal, Application, WorkflowRun, AgentRun, AuditLog, Document, UsageEvent, LoginAttempt, SystemEvent, Subscription

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user = Depends(require_admin)):
    if not feature_map(db, user).get("admin"):
        raise HTTPException(403, "Admin controls require an Enterprise or White Label plan.")
    return {
        "tenants": db.query(Tenant).count(),
        "users": db.query(User).filter(User.tenant_id == user.tenant_id).count(),
        "grants": db.query(Grant).count(),
        "proposals": db.query(Proposal).filter(Proposal.tenant_id == user.tenant_id).count(),
        "applications": db.query(Application).filter(Application.tenant_id == user.tenant_id).count(),
        "workflows": db.query(WorkflowRun).filter(WorkflowRun.tenant_id == user.tenant_id).count(),
        "agent_runs": db.query(AgentRun).count(),
        "documents": db.query(Document).filter(Document.tenant_id == user.tenant_id).count(),
        "usage_events": db.query(UsageEvent).filter(UsageEvent.tenant_id == user.tenant_id).count(),
        "audit_logs": db.query(AuditLog).filter(AuditLog.tenant_id == user.tenant_id).count(),
        "current_user_usage": usage_summary(db, user),
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db), user = Depends(require_admin)):
    if not feature_map(db, user).get("admin"):
        raise HTTPException(403, "Admin controls require an Enterprise or White Label plan.")
    rows = db.query(User).filter(User.tenant_id == user.tenant_id).order_by(User.created_at.desc()).limit(500).all()
    return [{"id": r.id, "email": r.email, "full_name": r.full_name, "role": r.role, "is_active": r.is_active, "email_verified": r.email_verified, "account_type": r.account_type, "created_at": r.created_at} for r in rows]

@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: dict, db: Session = Depends(get_db), user = Depends(require_admin)):
    if not feature_map(db, user).get("admin"):
        raise HTTPException(403, "Admin controls require an Enterprise or White Label plan.")
    target = db.query(User).filter(User.id == user_id, User.tenant_id == user.tenant_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if "is_active" in payload and payload["is_active"] is not None:
        target.is_active = bool(payload["is_active"])
    if "role" in payload and payload["role"] in {"member", "admin", "owner"}:
        target.role = payload["role"]
    if "plan" in payload and payload["plan"]:
        sub = db.query(Subscription).filter(Subscription.user_id == target.id).order_by(Subscription.id.desc()).first()
        if sub:
            sub.plan = payload["plan"]
            db.add(sub)
    db.add(target); db.commit()
    return {"ok": True}


@router.get("/plans")
def plans(db: Session = Depends(get_db), user = Depends(require_admin)):
    if not feature_map(db, user).get("admin"):
        raise HTTPException(403, "Admin controls require an Enterprise or White Label plan.")
    return {"plans": plan_matrix()}

@router.get("/preview/{plan}")
def preview_plan(plan: str, db: Session = Depends(get_db), user = Depends(require_admin)):
    if not feature_map(db, user).get("admin"):
        raise HTTPException(403, "Admin controls require an Enterprise or White Label plan.")
    return {"plan": plan, "features": feature_map(db, user, preview_plan=plan), "matrix": [p for p in plan_matrix() if p["plan"] == plan]}

@router.post("/users/{user_id}/credits")
def grant_user_credits(user_id: int, payload: dict, db: Session = Depends(get_db), user = Depends(require_admin)):
    if not feature_map(db, user).get("admin"):
        raise HTTPException(403, "Admin controls require an Enterprise or White Label plan.")
    target = db.query(User).filter(User.id == user_id, User.tenant_id == user.tenant_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    return add_credits(db, user, target, int(payload.get("credits", 0)), payload.get("reason") or "manual_admin_credit")

@router.get("/security")
def security_overview(db: Session = Depends(get_db), user = Depends(require_admin)):
    if not feature_map(db, user).get("admin"):
        raise HTTPException(403, "Admin controls require an Enterprise or White Label plan.")
    return {
        "failed_logins": db.query(LoginAttempt).filter(LoginAttempt.tenant_id == user.tenant_id, LoginAttempt.success == False).count(),
        "locked_users": db.query(User).filter(User.tenant_id == user.tenant_id, User.locked_until != None).count(),
        "system_events": db.query(SystemEvent).count(),
    }
