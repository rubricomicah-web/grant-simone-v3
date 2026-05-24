from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import current_user, require_admin
from app.models.tables import FundingMonitorRun
from app.services.monitoring import run_funding_monitor_once

router = APIRouter(prefix="/monitoring", tags=["Funding Monitoring"])

@router.post("/run-now")
def run_now(db: Session = Depends(get_db), user=Depends(require_admin)):
    result = run_funding_monitor_once(db, tenant_id=user.tenant_id)
    run = FundingMonitorRun(tenant_id=user.tenant_id, status="completed", result_json=result)
    db.add(run); db.commit(); db.refresh(run)
    return {"run_id": run.id, **result}

@router.get("/status")
def status(db: Session = Depends(get_db), user=Depends(current_user)):
    last = db.query(FundingMonitorRun).filter(FundingMonitorRun.tenant_id == user.tenant_id).order_by(FundingMonitorRun.id.desc()).first()
    return {"funding_monitor_enabled": settings.funding_monitor_enabled, "last_run": last.result_json if last else None}
