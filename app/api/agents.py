from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_paid_user
from app.models.tables import AgentRun, WorkflowRun
from app.agents.orchestrator import AGENTS
from app.services.serialize import model_to_dict
from app.services.plans import require_feature

router = APIRouter(prefix="/agents", tags=["AI Agents"])

@router.get("")
def list_available_agents(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "workflows")
    return {
        "agents": [
            {"name": "grant_hunter", "purpose": "Finds and selects verified funding opportunities."},
            {"name": "eligibility", "purpose": "Checks likely qualification and match quality."},
            {"name": "memory", "purpose": "Retrieves profile memory and past context."},
            {"name": "budget", "purpose": "Builds draft use-of-funds planning."},
            {"name": "compliance", "purpose": "Checks requirements and missing information."},
            {"name": "proposal_writer", "purpose": "Generates proposal/application narrative."},
            {"name": "reviewer", "purpose": "Scores proposal quality and alignment."},
            {"name": "submission_planner", "purpose": "Creates approval-gated application package."},
            {"name": "deadline_monitor", "purpose": "Tracks deadline and next action."},
            {"name": "notification", "purpose": "Creates platform alert when package is ready."},
        ],
        "default_pipeline": AGENTS,
    }

@router.get("/runs")
def list_agent_runs(workflow_id: int | None = None, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "workflows")
    q = db.query(AgentRun).join(WorkflowRun, WorkflowRun.id == AgentRun.workflow_run_id).filter(WorkflowRun.tenant_id == user.tenant_id)
    if workflow_id:
        q = q.filter(AgentRun.workflow_run_id == workflow_id)
    rows = q.order_by(AgentRun.created_at.desc()).limit(200).all()
    return [model_to_dict(r) for r in rows]

@router.get("/runs/{run_id}")
def get_agent_run(run_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "workflows")
    row = db.query(AgentRun).join(WorkflowRun, WorkflowRun.id == AgentRun.workflow_run_id).filter(AgentRun.id == run_id, WorkflowRun.tenant_id == user.tenant_id).first()
    if not row:
        raise HTTPException(404, "Agent run not found")
    return model_to_dict(row)
