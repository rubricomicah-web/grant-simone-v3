from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.models.tables import Application, BrowserAutomationTask, Grant, Organization, Document
from app.services.browser_agent import prepare_portal_draft

router = APIRouter(prefix="/automation", tags=["Automation"])

class BrowserPrepareRequest(BaseModel):
    application_id: int | None = None
    grant_id: int | None = None
    organization_id: int | None = None
    application_url: HttpUrl | None = None

@router.post("/browser/prepare")
async def prepare_browser_task(payload: BrowserPrepareRequest, db: Session = Depends(get_db), user=Depends(current_user)):
    app = None
    grant = None
    org = None
    if payload.application_id:
        app = db.query(Application).filter(Application.id == payload.application_id, Application.tenant_id == user.tenant_id).first()
        if not app:
            raise HTTPException(404, "Application not found")
        grant = db.query(Grant).filter(Grant.id == app.grant_id).first()
        org = db.query(Organization).filter(Organization.id == app.organization_id, Organization.tenant_id == user.tenant_id).first()
    else:
        if not payload.grant_id or not payload.organization_id:
            raise HTTPException(400, "application_id or grant_id + organization_id is required")
        grant = db.query(Grant).filter(Grant.id == payload.grant_id).first()
        org = db.query(Organization).filter(Organization.id == payload.organization_id, Organization.tenant_id == user.tenant_id).first()
    if not grant or not org:
        raise HTTPException(404, "Grant or profile not found")
    target = str(payload.application_url or grant.application_url or "")
    if not target:
        raise HTTPException(400, "No official application URL available")
    docs = db.query(Document).filter(Document.tenant_id == user.tenant_id, Document.organization_id == org.id).all()
    result = await prepare_portal_draft(target, {"name": org.name, "state": org.state, "goals": org.funding_goals}, {"title": grant.title, "url": target}, [{"filename": d.original_filename} for d in docs])
    task = BrowserAutomationTask(
        tenant_id=user.tenant_id,
        user_id=user.id,
        application_id=app.id if app else None,
        target_url=target,
        status=result.status,
        result_json={"message": result.message, "steps": result.steps, "portal_session_url": result.portal_session_url},
        approval_required=True,
    )
    db.add(task); db.commit(); db.refresh(task)
    return {"task_id": task.id, "status": task.status, "result": task.result_json, "approval_required": True}

@router.get("/browser/tasks")
def list_browser_tasks(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.query(BrowserAutomationTask).filter(BrowserAutomationTask.tenant_id == user.tenant_id).order_by(BrowserAutomationTask.id.desc()).limit(50).all()
    return [{"id": r.id, "status": r.status, "target_url": r.target_url, "approval_required": r.approval_required, "result": r.result_json, "created_at": r.created_at} for r in rows]
