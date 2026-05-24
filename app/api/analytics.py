from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.models.tables import Application, Proposal, WorkflowRun
from app.services.funding_health import compute_funding_health

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary")
def summary(db: Session = Depends(get_db), user = Depends(current_user)):
    apps = db.query(Application).filter(Application.tenant_id == user.tenant_id).all()
    return {
        "proposal_count": db.query(Proposal).filter(Proposal.tenant_id == user.tenant_id).count(),
        "workflow_count": db.query(WorkflowRun).filter(WorkflowRun.tenant_id == user.tenant_id).count(),
        "applications_by_status": {s: sum(1 for a in apps if a.status == s) for s in sorted({a.status for a in apps})},
    }


@router.get("/funding-health")
def funding_health(organization_id: int | None = None, db: Session = Depends(get_db), user = Depends(current_user)):
    return compute_funding_health(db, user, organization_id)
