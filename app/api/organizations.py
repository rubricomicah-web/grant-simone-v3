from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, require_paid_user
from app.models.tables import Organization
from app.schemas.api import OrganizationCreate
from app.services.serialize import model_to_dict

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.post("")
def create_org(payload: OrganizationCreate, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    row = Organization(tenant_id=user.tenant_id, owner_user_id=user.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return model_to_dict(row)

@router.get("")
def list_orgs(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    rows = db.query(Organization).filter(Organization.tenant_id == user.tenant_id).order_by(Organization.created_at.desc()).all()
    return [model_to_dict(r) for r in rows]

@router.get("/{org_id}")
def get_org(org_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    row = db.query(Organization).filter(Organization.id == org_id, Organization.tenant_id == user.tenant_id).first()
    if not row: raise HTTPException(404, "Organization not found")
    return model_to_dict(row)
