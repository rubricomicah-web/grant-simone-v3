from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.core.security import current_user, require_paid_user
from app.models.tables import WorkflowRun
from app.schemas.api import WorkflowStartRequest
from app.agents.orchestrator import run_workflow
from app.services.serialize import model_to_dict
from app.services.plans import check_and_record_usage, require_feature

router = APIRouter(prefix="/workflows", tags=["Workflows"])

def run_in_background(workflow_id: int):
    db = SessionLocal()
    try:
        run_workflow(db, workflow_id)
    finally:
        db.close()

@router.post("/start")
def start(payload: WorkflowStartRequest, background: BackgroundTasks, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "workflows")
    check_and_record_usage(db, user, "workflow_run", {"workflow": payload.workflow, "organization_id": payload.organization_id, "grant_id": payload.grant_id})
    row = WorkflowRun(tenant_id=user.tenant_id, organization_id=payload.organization_id, grant_id=payload.grant_id, workflow=payload.workflow, status="queued", result_json={"context": payload.context})
    db.add(row); db.commit(); db.refresh(row)
    background.add_task(run_in_background, row.id)
    return model_to_dict(row)

@router.get("")
def list_runs(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "workflows")
    rows = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == user.tenant_id).order_by(WorkflowRun.created_at.desc()).limit(100).all()
    return [model_to_dict(r) for r in rows]

@router.get("/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "workflows")
    row = db.query(WorkflowRun).filter(WorkflowRun.id == run_id, WorkflowRun.tenant_id == user.tenant_id).first()
    if not row: raise HTTPException(404, "Workflow not found")
    return model_to_dict(row)
