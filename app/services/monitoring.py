from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.tables import Organization, Grant, Notification, User
from app.services.grants import match_score, is_relevant_grant


def run_funding_monitor_once(db: Session, tenant_id: int | None = None) -> dict:
    """Scan profiles against verified grants already in DB. No fallback grants are generated."""
    q = db.query(Organization)
    if tenant_id:
        q = q.filter(Organization.tenant_id == tenant_id)
    profiles = q.limit(250).all()
    created = 0
    scanned = 0
    for org in profiles:
        scanned += 1
        owner = db.query(User).filter(User.id == org.owner_user_id).first()
        if not owner:
            continue
        query = " ".join(filter(None, [org.profile_type, org.org_type, org.state, org.funding_goals, org.mission]))
        grants = db.query(Grant).filter(Grant.verified == True).order_by(Grant.last_checked_at.desc()).limit(300).all()
        ranked = []
        for grant in grants:
            if not is_relevant_grant(grant, query or "funding", audience="all", category=None, state=org.state):
                continue
            score = match_score(grant, query or "funding")
            if score >= 65:
                ranked.append((score, grant))
        ranked.sort(key=lambda x: x[0], reverse=True)
        for score, grant in ranked[:3]:
            exists = db.query(Notification).filter(
                Notification.user_id == owner.id,
                Notification.organization_id == org.id,
                Notification.grant_id == grant.id,
                Notification.type == "grant_match",
            ).first()
            if exists:
                continue
            db.add(Notification(
                tenant_id=org.tenant_id,
                user_id=owner.id,
                organization_id=org.id,
                grant_id=grant.id,
                type="grant_match",
                title=f"New funding match: {grant.title[:120]}",
                message=f"Mogul Grant System found a verified funding opportunity that may fit {org.name}.",
                action_url=f"/signup.html#grants?grant_id={grant.id}",
                priority="high" if score >= 85 else "normal",
            ))
            created += 1
    db.commit()
    return {"ok": True, "profiles_scanned": scanned, "notifications_created": created, "timestamp": datetime.now(timezone.utc).isoformat()}
