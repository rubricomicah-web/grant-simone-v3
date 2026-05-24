from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, require_admin
from fastapi import HTTPException
from app.services.plans import user_can_white_label
from app.schemas.api import TenantUpdate
from app.services.serialize import model_to_dict

router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.get("/current")
def current_tenant(db: Session = Depends(get_db), user = Depends(current_user)):
    return model_to_dict(user.tenant)

@router.patch("/current")
def update_tenant(payload: TenantUpdate, db: Session = Depends(get_db), user = Depends(require_admin)):
    if not user_can_white_label(db, user):
        raise HTTPException(403, "White-label access requires a white-label plan.")
    tenant = user.tenant
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(tenant, k, v)
    db.commit(); db.refresh(tenant)
    return model_to_dict(tenant)
