from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, require_paid_user
from app.models.tables import Grant, SavedGrant, Organization
from app.schemas.api import GrantSearchRequest
from app.services.grants import discover, match_score, profile_text, match_details
from app.services.funding_engine import FundingRecommendationEngine
from app.services.serialize import model_to_dict
from app.services.plans import check_and_record_usage, require_feature, is_private_grant_category, plan_limits
from app.services.ingestion import ingest_live_grants
from app.schemas.api import IngestRequest

router = APIRouter(prefix="/grants", tags=["Grants"])

@router.post("/search")
async def search(payload: GrantSearchRequest, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "grant_search")
    if is_private_grant_category(payload.category) and not plan_limits(db, user).get("private_grants", False):
        raise HTTPException(status_code=403, detail="Private and corporate grant intelligence is not included in your current plan. Please upgrade to Individual Elite, Business Owner, or White Label Platform.")
    check_and_record_usage(db, user, "grant_search", {"query": payload.query, "audience": payload.audience, "category": payload.category})
    org = None
    org_text = payload.query
    audience = payload.audience
    if payload.organization_id:
        org = db.query(Organization).filter(Organization.id == payload.organization_id, Organization.tenant_id == user.tenant_id).first()
        if org:
            org_text = profile_text(org, payload.query) + " " + payload.query
            if audience == "all":
                audience = "individual" if org.profile_type in {"individual", "student", "artist", "veteran", "family", "homeowner"} else "organization"
    rows = await discover(db, payload.query or "funding assistance", payload.state, payload.limit, audience=audience, category=payload.category)
    data = []
    allow_private = bool(plan_limits(db, user).get("private_grants", False))
    for r in rows:
        raw = r.raw_json or {}
        source_kind = str(raw.get("source_kind") or raw.get("funding_type") or "").lower() if isinstance(raw, dict) else ""
        if not allow_private and (r.category in {"private", "corporate"} or "private" in source_kind or "corporate" in source_kind):
            continue
        d = model_to_dict(r)
        score = match_score(r, org_text)
        d["match_score"] = score
        d["profile_audience"] = audience
        details = match_details({
            "title": r.title,
            "description": r.description,
            "eligibility": r.eligibility,
            "audience": r.audience,
            "category": r.category,
            "state": r.state,
            "source": r.source,
            "verified": r.verified,
            "raw_json": r.raw_json or {},
        }, payload.query or org_text, payload.state)
        d["match_details"] = details
        d["recommendation"] = FundingRecommendationEngine.recommendation(score, [details.get("reason", "Verified profile match")])
        data.append(d)
    data.sort(key=lambda x: (x.get("match_score", 0), x.get("confidence_score", 0)), reverse=True)
    message = None
    if not data:
        message = "No verified relevant grants found for this state and need yet. No dummy grants are shown. Try a broader need, select All USA, or add more verified sources."
    return {"grants": data, "audience": audience, "category": payload.category, "message": message}

@router.get("")
def list_grants(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "grant_search")
    rows = db.query(Grant).order_by(Grant.last_checked_at.desc()).limit(100).all()
    return [model_to_dict(r) for r in rows]

@router.post("/{grant_id}/save")
def save_grant(grant_id: int, organization_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    if not db.get(Grant, grant_id): raise HTTPException(404, "Grant not found")
    org = db.query(Organization).filter(Organization.id == organization_id, Organization.tenant_id == user.tenant_id).first()
    if not org: raise HTTPException(404, "Funding profile not found")
    row = SavedGrant(tenant_id=user.tenant_id, organization_id=organization_id, grant_id=grant_id)
    db.add(row); db.commit(); db.refresh(row)
    return model_to_dict(row)


@router.post("/ingest-live")
async def ingest_live(payload: IngestRequest, db: Session = Depends(get_db), user = Depends(current_user)):
    if user.role not in {"owner", "admin"}:
        raise HTTPException(403, "Admin access required")
    return await ingest_live_grants(db, payload.query, payload.state, payload.limit)
