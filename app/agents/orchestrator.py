from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.tables import WorkflowRun, AgentRun, Organization, Grant, Proposal, Application, Memory, Notification
from app.services.ai import generate_proposal, score_proposal
from app.services.pdf import proposal_pdf
from app.services.grants import match_score, profile_text, discover
from app.services.serialize import model_to_dict

AGENTS = [
    "grant_hunter",
    "eligibility",
    "memory",
    "budget",
    "compliance",
    "proposal_writer",
    "reviewer",
    "submission_planner",
    "deadline_monitor",
    "notification",
]


def log_agent(db: Session, run_id: int, name: str, input_json: dict, output_json: dict, status: str = "completed") -> AgentRun:
    """Create or update the latest agent state for a workflow.

    Earlier builds appended a new card every time an agent wrote output, which made
    the UI look like a debug dump. For the product experience, each workflow should
    show one clean state per agent.
    """
    row = db.query(AgentRun).filter(
        AgentRun.workflow_run_id == run_id,
        AgentRun.agent_name == name,
    ).first()
    if row:
        row.input_json = input_json or {}
        row.output_json = output_json or {}
        row.status = status
        row.created_at = datetime.now(timezone.utc)
    else:
        row = AgentRun(
            workflow_run_id=run_id,
            agent_name=name,
            input_json=input_json or {},
            output_json=output_json or {},
            status=status,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # BackgroundTasks normally run in a worker thread without a running loop.
    # If a loop exists, create a temporary one safely in a fresh thread-like path.
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()


def _agent_error(db: Session, workflow: WorkflowRun, agent: str, message: str, payload: dict | None = None) -> dict:
    output = {"error": message, **(payload or {})}
    log_agent(db, workflow.id, agent, payload or {}, output, status="failed")
    workflow.status = "failed"
    workflow.result_json = output
    workflow.updated_at = datetime.now(timezone.utc)
    db.commit()
    return output


def grant_hunter_agent(db: Session, workflow: WorkflowRun, org: Organization) -> Grant | None:
    """Find or select the strongest verified opportunity for the profile.

    If the user already selected a grant, this agent verifies that grant.
    If not, it searches verified opportunities in the database/live official sources and picks the
    highest scoring match. It never creates dummy or fallback grants.
    """
    query = profile_text(org, "funding assistance") or "funding assistance"
    audience = "individual" if org.profile_type in {"individual", "student", "artist", "veteran", "family", "homeowner"} else "organization"

    if workflow.grant_id:
        grant = db.get(Grant, workflow.grant_id)
        if grant:
            score = match_score(grant, query)
            log_agent(db, workflow.id, "grant_hunter", {"selected_grant_id": grant.id}, {"mode": "user_selected", "grant_id": grant.id, "title": grant.title, "match_score": score})
            return grant

    grants = _run_async(discover(db, query, org.state, 10, audience=audience, category=None))
    ranked = sorted(grants, key=lambda g: (match_score(g, query), g.confidence_score or 0), reverse=True)
    selected = ranked[0] if ranked else None
    log_agent(
        db,
        workflow.id,
        "grant_hunter",
        {"query": query, "audience": audience, "state": org.state},
        {
            "found": len(ranked),
            "selected_grant_id": selected.id if selected else None,
            "selected_title": selected.title if selected else None,
            "top_matches": [{"id": g.id, "title": g.title, "score": match_score(g, query), "source": g.source} for g in ranked[:5]],
        },
    )
    if selected:
        workflow.grant_id = selected.id
        db.commit()
    return selected


def eligibility_agent(db: Session, workflow: WorkflowRun, org: Organization, grant: Grant, memory_text: str) -> dict:
    score = match_score(grant, f"{profile_text(org)} {memory_text}")
    reasons = []
    if grant.audience in {"all", "individual" if org.profile_type == "individual" else "organization"}:
        reasons.append("Audience type appears aligned.")
    if org.state and (not grant.state or grant.state == org.state):
        reasons.append("Location does not conflict with the opportunity.")
    if grant.verified:
        reasons.append("Source is marked verified.")
    result = {
        "eligible_likely": score >= 70,
        "match_score": score,
        "recommendation": "proceed" if score >= 70 else "review manually before applying",
        "reasons": reasons or ["Profile and opportunity have partial keyword alignment."],
    }
    log_agent(db, workflow.id, "eligibility", {"organization_id": org.id, "grant_id": grant.id}, result)
    return result


def memory_agent(db: Session, workflow: WorkflowRun, org: Organization) -> str:
    memories = db.query(Memory).filter(Memory.organization_id == org.id).order_by(Memory.importance.desc()).limit(12).all()
    memory_text = "\n".join(m.content for m in memories)
    log_agent(db, workflow.id, "memory", {"organization_id": org.id}, {"memories_used": len(memories), "has_memory": bool(memory_text)})
    return memory_text


def budget_agent(db: Session, workflow: WorkflowRun, org: Organization, grant: Grant) -> dict:
    requested = org.annual_budget or grant.amount_max or grant.amount_min or 10000
    budget = {
        "requested_amount_estimate": requested,
        "categories": [
            {"name": "Program or project delivery", "percent": 45},
            {"name": "Equipment, software, or materials", "percent": 25},
            {"name": "Training, staffing, or contractor support", "percent": 20},
            {"name": "Measurement, reporting, and contingency", "percent": 10},
        ],
        "note": "Budget is a planning draft. User should confirm final line items before submission.",
    }
    log_agent(db, workflow.id, "budget", {"organization_id": org.id, "grant_id": grant.id}, budget)
    return budget


def compliance_agent(db: Session, workflow: WorkflowRun, org: Organization, grant: Grant) -> dict:
    missing = []
    if not org.funding_goals:
        missing.append("funding goals")
    if not org.state:
        missing.append("state/location")
    if not grant.application_url:
        missing.append("official application link verification")
    checklist = {
        "required": [
            "funding profile",
            "official grant page review",
            "proposal/application narrative",
            "budget or use-of-funds plan",
            "supporting documents",
            "client approval before submission",
        ],
        "missing": missing,
        "approval_gate": True,
        "risk_level": "low" if grant.verified and not missing else "medium",
        "submission_rule": "Do not submit automatically without explicit user approval.",
    }
    log_agent(db, workflow.id, "compliance", {"organization_id": org.id, "grant_id": grant.id}, checklist)
    return checklist


def proposal_agent(db: Session, workflow: WorkflowRun, org: Organization, grant: Grant, memory_text: str, budget: dict) -> Proposal:
    clean_purpose = org.funding_goals or org.mission or "business growth, operations, marketing, staffing, supplies, and training"
    requested_amount = float(budget.get("requested_amount_estimate") or 0) or None
    body = generate_proposal(model_to_dict(org), model_to_dict(grant), requested_amount, clean_purpose)
    review = score_proposal(body, model_to_dict(grant))
    pdf_path = proposal_pdf(f"{org.name} - {grant.title}", body)
    proposal = Proposal(
        tenant_id=workflow.tenant_id,
        organization_id=org.id,
        grant_id=grant.id,
        title=f"{org.name} - {grant.title}",
        body=body,
        score=float(review.get("score", 75)),
        review_json=review,
        pdf_path=pdf_path,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    log_agent(db, workflow.id, "proposal_writer", {"organization_id": org.id, "grant_id": grant.id}, {"proposal_id": proposal.id, "score": proposal.score, "pdf_ready": bool(pdf_path)})
    log_agent(db, workflow.id, "reviewer", {"proposal_id": proposal.id}, review)
    return proposal


def submission_agent(db: Session, workflow: WorkflowRun, org: Organization, grant: Grant, proposal: Proposal, checklist: dict) -> Application:
    app = Application(
        tenant_id=workflow.tenant_id,
        organization_id=org.id,
        grant_id=grant.id,
        proposal_id=proposal.id,
        status="ready_for_client_approval",
        approval_required=True,
        checklist_json=checklist,
        notes="Application package prepared for client review. Final submission must be completed by the user on the official funder website.",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    log_agent(db, workflow.id, "submission_planner", {"proposal_id": proposal.id}, {"application_id": app.id, "status": app.status, "approval_required": True, "official_link": grant.application_url})
    return app


def deadline_monitor_agent(db: Session, workflow: WorkflowRun, grant: Grant, app: Application) -> dict:
    result = {
        "deadline": grant.deadline or "Verify on official grant page",
        "monitoring_status": "tracking_created",
        "application_id": app.id,
        "next_action": "Review proposal and approve application package.",
    }
    log_agent(db, workflow.id, "deadline_monitor", {"grant_id": grant.id, "application_id": app.id}, result)
    return result


def notification_agent(db: Session, workflow: WorkflowRun, org: Organization, grant: Grant, app: Application) -> dict:
    title = f"Application package ready: {grant.title[:120]}"
    message = "Mogul Grant System prepared a proposal and application plan. Review and approve before submission."
    notification = Notification(
        tenant_id=workflow.tenant_id,
        user_id=org.owner_user_id,
        organization_id=org.id,
        grant_id=grant.id,
        type="workflow_ready",
        title=title,
        message=message,
        action_url=f"/signup.html#apps?application_id={app.id}",
        priority="high",
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    result = {"notification_id": notification.id, "title": title, "platform_alert_created": True}
    log_agent(db, workflow.id, "notification", {"application_id": app.id}, result)
    return result


def run_full_grant_pipeline(db: Session, workflow: WorkflowRun) -> dict:
    org = db.get(Organization, workflow.organization_id) if workflow.organization_id else None
    if not org:
        return _agent_error(db, workflow, "eligibility", "organization_id is required. Create/select a funding profile first.", {"organization_id": workflow.organization_id})

    grant = grant_hunter_agent(db, workflow, org)
    if not grant:
        return _agent_error(db, workflow, "grant_hunter", "No verified funding opportunity could be found for this profile.", {"organization_id": org.id})

    memory_text = memory_agent(db, workflow, org)
    eligibility = eligibility_agent(db, workflow, org, grant, memory_text)
    budget = budget_agent(db, workflow, org, grant)
    checklist = compliance_agent(db, workflow, org, grant)
    proposal = proposal_agent(db, workflow, org, grant, memory_text, budget)
    app = submission_agent(db, workflow, org, grant, proposal, checklist)
    deadline = deadline_monitor_agent(db, workflow, grant, app)
    note = notification_agent(db, workflow, org, grant, app)

    result = {
        "workflow_id": workflow.id,
        "organization_id": org.id,
        "grant_id": grant.id,
        "grant_title": grant.title,
        "match_score": eligibility.get("match_score"),
        "proposal_id": proposal.id,
        "application_id": app.id,
        "status": "ready_for_client_approval",
        "approval_required": True,
        "official_application_url": grant.application_url,
        "deadline": deadline.get("deadline"),
        "notification_id": note.get("notification_id"),
        "agents_completed": AGENTS,
    }
    workflow.status = "completed"
    workflow.result_json = result
    workflow.updated_at = datetime.now(timezone.utc)
    db.commit()
    return result


def run_workflow(db: Session, workflow_id: int) -> dict:
    workflow = db.get(WorkflowRun, workflow_id)
    if not workflow:
        return {"error": "workflow not found"}
    workflow.status = "running"
    workflow.updated_at = datetime.now(timezone.utc)
    db.commit()
    if workflow.workflow == "full_grant_pipeline":
        return run_full_grant_pipeline(db, workflow)
    return _agent_error(db, workflow, "orchestrator", "unknown workflow", {"workflow": workflow.workflow})
