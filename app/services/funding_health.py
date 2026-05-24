from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.tables import Organization, Document, Proposal, Application, WorkflowRun, FundingOutcome, Grant


def _clamp(v: float, low: float = 0, high: float = 100) -> int:
    return int(max(low, min(high, round(v))))


def _label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Strong"
    if score >= 70:
        return "Competitive"
    if score >= 60:
        return "Needs Improvement"
    return "High Risk"


def _days_until_deadline(deadline: str | None):
    if not deadline:
        return None
    text = str(deadline).strip().lower()
    if "rolling" in text or "ongoing" in text:
        return 90
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            dt = datetime.strptime(str(deadline).strip(), fmt).replace(tzinfo=timezone.utc)
            return (dt - datetime.now(timezone.utc)).days
        except Exception:
            pass
    return None


def _profile_completeness(org: Organization | None) -> tuple[int, list[str], list[str]]:
    if not org:
        return 20, [], ["Create a funding profile"]
    fields = [
        org.name,
        org.profile_type,
        org.state,
        org.city,
        org.funding_goals,
        org.annual_budget or org.annual_income,
        org.mission or org.education_level,
    ]
    completed = sum(1 for f in fields if f not in (None, "", []))
    score = 35 + (completed / len(fields)) * 60
    strengths = []
    risks = []
    if org.funding_goals:
        strengths.append("Funding goal is documented")
    else:
        risks.append("Funding goal is missing")
    if org.state:
        strengths.append("Geography is available for matching")
    else:
        risks.append("State/location is missing")
    if org.annual_budget or org.annual_income:
        strengths.append("Budget/income context is available")
    else:
        risks.append("Budget or income context is missing")
    return _clamp(score), strengths, risks


def compute_funding_health(db: Session, user, organization_id: int | None = None) -> dict:
    tenant_id = user.tenant_id
    org_query = db.query(Organization).filter(Organization.tenant_id == tenant_id)
    if organization_id:
        org_query = org_query.filter(Organization.id == organization_id)
    org = org_query.order_by(Organization.created_at.desc()).first()

    docs_count = db.query(Document).filter(Document.tenant_id == tenant_id).count()
    proposals = db.query(Proposal).filter(Proposal.tenant_id == tenant_id).all()
    apps = db.query(Application).filter(Application.tenant_id == tenant_id).all()
    workflows = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == tenant_id).all()
    outcomes = db.query(FundingOutcome).filter(FundingOutcome.tenant_id == tenant_id).all()

    latest_proposal_score = max([float(p.score or 0) for p in proposals], default=0)
    ready_apps = sum(1 for a in apps if a.status in {"ready_for_client_approval", "approved", "submitted", "under_review", "awarded"})
    submitted_apps = sum(1 for a in apps if a.status in {"submitted", "under_review", "awarded"})
    completed_workflows = sum(1 for w in workflows if w.status == "completed")
    awards = [o for o in outcomes if o.status == "awarded"]

    profile_score, strengths, risks = _profile_completeness(org)

    eligibility_score = 50
    if org:
        eligibility_score += 10 if org.state else 0
        eligibility_score += 15 if org.funding_goals else 0
        eligibility_score += 10 if org.profile_type else 0
        eligibility_score += 10 if (org.eligibility_tags or org.veteran_status or org.disability_status) else 0
        eligibility_score += 5 if org.annual_budget or org.annual_income else 0
    eligibility_score = _clamp(eligibility_score)

    readiness_score = profile_score
    readiness_score += min(20, docs_count * 5)
    readiness_score += 10 if completed_workflows else 0
    readiness_score = _clamp(readiness_score)

    proposal_score = latest_proposal_score if latest_proposal_score else (55 if proposals else 25)
    proposal_score = _clamp(proposal_score)

    financial_score = 55
    if org and (org.annual_budget or org.annual_income):
        financial_score += 25
    if docs_count >= 2:
        financial_score += 10
    if proposals:
        financial_score += 5
    financial_score = _clamp(financial_score)

    compliance_score = 45
    if org and org.state:
        compliance_score += 10
    if docs_count:
        compliance_score += 15
    if ready_apps:
        compliance_score += 20
    if all((a.checklist_json or {}).get("approval_gate", True) for a in apps) if apps else True:
        compliance_score += 5
    compliance_score = _clamp(compliance_score)

    history_score = 45
    if submitted_apps:
        history_score += min(30, submitted_apps * 10)
    if awards:
        history_score += 25
    history_score = _clamp(history_score)

    timing_score = 70
    grant_ids = [a.grant_id for a in apps if a.grant_id]
    if grant_ids:
        grants = db.query(Grant).filter(Grant.id.in_(grant_ids)).all()
        days = [_days_until_deadline(g.deadline) for g in grants]
        valid_days = [d for d in days if d is not None]
        if valid_days:
            min_days = min(valid_days)
            if min_days < 0:
                timing_score = 20
            elif min_days < 7:
                timing_score = 45
            elif min_days < 21:
                timing_score = 70
            else:
                timing_score = 90
    elif completed_workflows:
        timing_score = 75
    timing_score = _clamp(timing_score)

    weights = {
        "eligibility_match": 0.25,
        "organization_readiness": 0.20,
        "proposal_strength": 0.20,
        "financial_stability": 0.15,
        "compliance_readiness": 0.10,
        "historical_performance": 0.05,
        "submission_timing": 0.05,
    }
    components = {
        "eligibility_match": eligibility_score,
        "organization_readiness": readiness_score,
        "proposal_strength": proposal_score,
        "financial_stability": financial_score,
        "compliance_readiness": compliance_score,
        "historical_performance": history_score,
        "submission_timing": timing_score,
    }
    score = _clamp(sum(components[k] * weights[k] for k in components))

    if latest_proposal_score >= 80:
        strengths.append("Latest proposal is scoring strong")
    elif proposals:
        risks.append("Proposal needs improvement before submission")
    else:
        risks.append("No proposal draft has been generated yet")
    if docs_count >= 2:
        strengths.append("Supporting documents are available")
    else:
        risks.append("Upload budgets, certifications, or prior materials")
    if completed_workflows:
        strengths.append("AI agent pipeline has completed at least one run")
    else:
        risks.append("Run the agent pipeline to validate eligibility and readiness")
    if ready_apps:
        strengths.append("Application package exists for review")

    recommended_actions = []
    if not org:
        recommended_actions.append("Create your first funding profile")
    if docs_count < 2:
        recommended_actions.append("Upload at least two supporting documents")
    if not proposals:
        recommended_actions.append("Generate a funder-specific proposal draft")
    if not completed_workflows:
        recommended_actions.append("Run the autonomous funding pipeline")
    if org and not (org.annual_budget or org.annual_income):
        recommended_actions.append("Add budget, income, or financial context")
    if not recommended_actions:
        recommended_actions.append("Review the best-matched opportunity and approve the package")

    return {
        "score": score,
        "label": _label(score),
        "components": components,
        "weights": weights,
        "strengths": strengths[:5],
        "risks": risks[:5],
        "recommended_actions": recommended_actions[:5],
        "profile_id": org.id if org else None,
        "profile_name": org.name if org else None,
        "computed_from": {
            "documents": docs_count,
            "proposals": len(proposals),
            "applications": len(apps),
            "completed_workflows": completed_workflows,
            "submitted_applications": submitted_apps,
            "awards": len(awards),
        },
        "formula": "25% eligibility + 20% readiness + 20% proposal + 15% financial + 10% compliance + 5% history + 5% timing",
    }
