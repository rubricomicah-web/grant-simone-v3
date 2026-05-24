from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, require_paid_user
from app.models.tables import Application, Organization, Grant, Proposal
from app.schemas.api import ApplicationCreate
from app.services.serialize import model_to_dict

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("")
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    org = db.query(Organization).filter(Organization.id == payload.organization_id, Organization.tenant_id == user.tenant_id).first()
    if not org or not db.get(Grant, payload.grant_id): raise HTTPException(404, "Organization or grant not found")
    row = Application(tenant_id=user.tenant_id, organization_id=payload.organization_id, grant_id=payload.grant_id, proposal_id=payload.proposal_id, notes=payload.notes, checklist_json={"approval_gate": True})
    db.add(row); db.commit(); db.refresh(row)
    return application_payload(row, db)

def application_payload(row: Application, db: Session):
    data = model_to_dict(row)
    org = db.query(Organization).filter(Organization.id == row.organization_id, Organization.tenant_id == row.tenant_id).first()
    grant = db.query(Grant).filter(Grant.id == row.grant_id).first()
    proposal = db.query(Proposal).filter(Proposal.id == row.proposal_id, Proposal.tenant_id == row.tenant_id).first() if row.proposal_id else None
    data["organization"] = model_to_dict(org) if org else None
    data["grant"] = model_to_dict(grant) if grant else None
    data["proposal"] = model_to_dict(proposal) if proposal else None
    return data

@router.get("")
def list_applications(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    rows = db.query(Application).filter(Application.tenant_id == user.tenant_id).order_by(Application.created_at.desc()).all()
    return [application_payload(r, db) for r in rows]

@router.get("/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    row = db.query(Application).filter(Application.id == application_id, Application.tenant_id == user.tenant_id).first()
    if not row: raise HTTPException(404, "Application not found")
    return application_payload(row, db)

@router.post("/{application_id}/approve")
def approve(application_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    row = db.query(Application).filter(Application.id == application_id, Application.tenant_id == user.tenant_id).first()
    if not row: raise HTTPException(404, "Application not found")
    row.status = "approved_ready_to_submit"; db.commit(); db.refresh(row)
    return application_payload(row, db)

@router.post("/{application_id}/mark-submitted")
def mark_submitted(application_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    row = db.query(Application).filter(Application.id == application_id, Application.tenant_id == user.tenant_id).first()
    if not row: raise HTTPException(404, "Application not found")
    if row.approval_required and row.status != "approved_ready_to_submit":
        raise HTTPException(400, "Client approval required before submission")
    row.status = "submitted"; row.submitted_at = datetime.now(timezone.utc); db.commit(); db.refresh(row)
    return application_payload(row, db)
