from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, require_paid_user, decode_token
from app.models.tables import Organization, Grant, Proposal, ProposalVersion, Application
from app.schemas.api import ProposalRequest, ProposalUpdate
from app.services.ai import generate_proposal, score_proposal
from app.services.pdf import proposal_pdf
from app.services.serialize import model_to_dict
from app.services.plans import check_and_record_usage, require_feature

router = APIRouter(prefix="/proposals", tags=["Proposals"])

@router.post("/generate")
def generate(payload: ProposalRequest, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "proposals")
    check_and_record_usage(db, user, "proposal_generate", {"organization_id": payload.organization_id, "grant_id": payload.grant_id})
    org = db.query(Organization).filter(Organization.id == payload.organization_id, Organization.tenant_id == user.tenant_id).first()
    if not org: raise HTTPException(404, "Organization not found")
    grant = db.get(Grant, payload.grant_id) if payload.grant_id else None
    org_data = model_to_dict(org); grant_data = model_to_dict(grant) if grant else {"title": payload.grant_name}
    body = generate_proposal(org_data, grant_data, payload.requested_amount, payload.funding_purpose)
    review = score_proposal(body, grant_data)
    title = f"{org.name} - {(grant.title if grant else payload.grant_name or 'Grant Proposal')}"
    pdf_path = proposal_pdf(title, body)
    row = Proposal(tenant_id=user.tenant_id, organization_id=org.id, grant_id=payload.grant_id, title=title, body=body, score=float(review.get("score", 75)), review_json=review, pdf_path=pdf_path)
    db.add(row); db.commit(); db.refresh(row)
    db.add(ProposalVersion(proposal_id=row.id, tenant_id=user.tenant_id, version_number=1, title=row.title, body=row.body, created_by_user_id=user.id))
    application_id = None
    if payload.grant_id:
        existing = db.query(Application).filter(Application.tenant_id == user.tenant_id, Application.organization_id == org.id, Application.grant_id == payload.grant_id, Application.proposal_id == row.id).first()
        app = existing or Application(tenant_id=user.tenant_id, organization_id=org.id, grant_id=payload.grant_id, proposal_id=row.id, status="draft", checklist_json={"approval_gate": True, "proposal_pdf": True, "official_application_required": True})
        if not existing:
            db.add(app)
        db.commit(); db.refresh(app)
        application_id = app.id
    else:
        db.commit()
    data = model_to_dict(row)
    data["application_id"] = application_id
    return data

@router.get("")
def list_proposals(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "proposals")
    rows = db.query(Proposal).filter(Proposal.tenant_id == user.tenant_id).order_by(Proposal.created_at.desc()).all()
    out = []
    for r in rows:
        data = model_to_dict(r)
        app = db.query(Application).filter(Application.tenant_id == user.tenant_id, Application.proposal_id == r.id).order_by(Application.created_at.desc()).first()
        data["application_id"] = app.id if app else None
        out.append(data)
    return out

@router.get("/{proposal_id}/pdf")
def download_pdf(proposal_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "proposals")
    require_feature(db, user, "pdf_exports")
    check_and_record_usage(db, user, "pdf_export", {"proposal_id": proposal_id})
    row = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.tenant_id == user.tenant_id).first()
    if not row or not row.pdf_path: raise HTTPException(404, "PDF not found")
    from pathlib import Path
    pdf = Path(row.pdf_path)
    if not pdf.exists():
        raise HTTPException(404, "PDF file is missing. Please regenerate the proposal.")
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (row.title or "application_narrative")).strip().replace(" ", "_")[:90]
    return FileResponse(str(pdf), media_type="application/pdf", filename=f"{safe_title}_Application_Narrative.pdf")


@router.get("/{proposal_id}")
def get_proposal(proposal_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "proposals")
    row = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.tenant_id == user.tenant_id).first()
    if not row:
        raise HTTPException(404, "Proposal not found")
    return model_to_dict(row)

@router.patch("/{proposal_id}")
def update_proposal(proposal_id: int, payload: ProposalUpdate, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "proposals")
    row = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.tenant_id == user.tenant_id).first()
    if not row:
        raise HTTPException(404, "Proposal not found")
    current_version = db.query(ProposalVersion).filter(ProposalVersion.proposal_id == row.id).count() + 1
    row.title = payload.title or row.title
    row.body = payload.body
    row.pdf_path = proposal_pdf(row.title, row.body)
    db.add(ProposalVersion(proposal_id=row.id, tenant_id=user.tenant_id, version_number=current_version, title=row.title, body=row.body, created_by_user_id=user.id))
    db.commit(); db.refresh(row)
    return model_to_dict(row)

@router.get("/{proposal_id}/versions")
def proposal_versions(proposal_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "proposals")
    row = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.tenant_id == user.tenant_id).first()
    if not row:
        raise HTTPException(404, "Proposal not found")
    versions = db.query(ProposalVersion).filter(ProposalVersion.proposal_id == proposal_id, ProposalVersion.tenant_id == user.tenant_id).order_by(ProposalVersion.version_number.desc()).all()
    return [model_to_dict(v) for v in versions]
