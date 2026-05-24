from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.models.tables import Application, FundingOutcome

router = APIRouter(prefix="/outcomes", tags=["Funding Outcomes"])

class OutcomeRequest(BaseModel):
    application_id: int
    status: str
    amount_awarded: float | None = None
    notes: str | None = None

@router.post("")
def record_outcome(payload: OutcomeRequest, db: Session = Depends(get_db), user=Depends(current_user)):
    app = db.query(Application).filter(Application.id == payload.application_id, Application.tenant_id == user.tenant_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    outcome = FundingOutcome(tenant_id=user.tenant_id, organization_id=app.organization_id, application_id=app.id, status=payload.status, amount_awarded=payload.amount_awarded, notes=payload.notes)
    app.status = payload.status
    db.add(outcome); db.commit(); db.refresh(outcome)
    return {"id": outcome.id, "status": outcome.status, "amount_awarded": outcome.amount_awarded}

@router.get("/summary")
def summary(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.query(FundingOutcome).filter(FundingOutcome.tenant_id == user.tenant_id).all()
    total_won = sum(float(r.amount_awarded or 0) for r in rows if r.status == "awarded")
    return {"total_outcomes": len(rows), "awarded": len([r for r in rows if r.status == "awarded"]), "rejected": len([r for r in rows if r.status == "rejected"]), "under_review": len([r for r in rows if r.status == "under_review"]), "total_won": total_won}
