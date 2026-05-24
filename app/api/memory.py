from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, require_paid_user
from app.models.tables import Memory, Organization
from app.schemas.api import MemoryCreate
from app.services.serialize import model_to_dict

router = APIRouter(prefix="/memory", tags=["Memory"])

@router.post("")
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    org = db.query(Organization).filter(Organization.id == payload.organization_id, Organization.tenant_id == user.tenant_id).first()
    if not org: raise HTTPException(404, "Organization not found")
    row = Memory(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return model_to_dict(row)

@router.get("/{organization_id}")
def list_memory(organization_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    rows = db.query(Memory).filter(Memory.tenant_id == user.tenant_id, Memory.organization_id == organization_id).order_by(Memory.importance.desc()).all()
    return [model_to_dict(r) for r in rows]
