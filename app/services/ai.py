import json
import re
from app.core.config import settings
from app.services.proposal_stabilizer import sanitize_proposal_text, stabilize_sections, is_submission_safe

SYSTEM = """You are an elite professional funding strategist and grant writer. You prepare client-voice, submission-ready funding narratives for businesses, nonprofits, startups, students, artists, veterans, families, homeowners, and individuals. Be accurate, practical, compliant, and never invent deadlines or official requirements. If data is missing, say what is missing."""


def _clean_purpose(value) -> str | None:
    if not value:
        return None
    text = str(value)
    # Remove internal context labels and Python/JSON-looking dumps before writing client-facing proposals.
    for marker in ["\n\nMemory:", "\nMemory:", "Memory:", "\n\nBudget draft:", "\nBudget draft:", "Budget draft:"]:
        text = text.replace(marker, " ")
    text = re.sub(r"\{[^{}]*(requested_amount_estimate|categories|note)[^{}]*\}", " ", text, flags=re.I|re.S)
    text = re.sub(r"\[[^\]]*(name|percent|requested_amount_estimate)[^\]]*\]", " ", text, flags=re.I|re.S)
    text = re.sub(r"\s+", " ", text).strip(" .;:-")
    if not text or text.lower() in {"none", "null", "not available"}:
        return None
    return text[:600]

def _fallback_narrative(org: dict, grant: dict | None, requested_amount: float | None, purpose: str | None) -> str:
    """Premium client-voice fallback. Never expose platform or AI authorship."""
    grant = grant or {}
    profile_type = (org.get("profile_type") or org.get("org_type") or "organization").lower()
    is_individual = profile_type in {"individual", "student", "artist", "veteran", "family", "homeowner"}
    name = org.get("name") or ("I" if is_individual else "our organization")
    grant_name = grant.get("title") or "this funding opportunity"
    amount = f"${requested_amount:,.0f}" if isinstance(requested_amount, (int, float)) and requested_amount else "the requested funding"
    goal = _clean_purpose(purpose) or org.get("funding_goals") or org.get("mission") or "the funding need described in this application"
    location = ", ".join([x for x in [org.get("city"), org.get("state")] if x]) or "our community"
    if is_individual:
        return f"""Applicant Summary
My name is {name}, and I am applying for {grant_name} to support {goal}. This funding would help me address a clear need, move forward with a meaningful goal, and create a stronger path toward stability and progress.

Personal Need
I am seeking support because the cost of {goal} creates a financial barrier that is difficult to manage without outside funding. This opportunity would allow me to move forward responsibly while focusing on the intended outcome of the grant.

Funding Goal
The requested support is {amount}. These funds would be used only for eligible expenses connected to {goal}. I will review the official requirements carefully and provide any documentation requested by the funder.

Use of Funds
Funding would be used for direct costs tied to the stated goal. This may include supplies, fees, training, services, materials, transportation, technology, documentation, or other eligible expenses approved by the funder.

Expected Outcome
If selected, I expect this funding to help me complete the proposed activity, reduce financial pressure, and create measurable progress toward my personal, educational, professional, housing, health, or community objective.

Eligibility Alignment
Based on the information available, my profile appears aligned with the purpose of {grant_name}. I will confirm all eligibility requirements, deadlines, and required attachments directly through the official funder before submission.

Conclusion
I respectfully request consideration for {grant_name}. This support would make a meaningful difference and help me take the next step toward the outcome described in this application.
"""
    return f"""Executive Summary
We are requesting {amount} from {grant_name} to support {goal}. Based in {location}, our team is prepared to use this funding to strengthen capacity, improve execution, and produce measurable results. The proposed investment will help us move from planning and early implementation into a more consistent, accountable, and scalable phase of work.

Applicant Overview
{name} operates as a {profile_type} applicant focused on practical execution, customer or community value, and responsible growth. Our work is rooted in clear service delivery, thoughtful planning, and a commitment to using outside funding only for eligible, high-impact activities.

Statement of Need / Problem Description
The need for this project is driven by the cost and operational demands associated with {goal}. Without grant support, our ability to expand, improve delivery, purchase needed materials, and execute the project timeline would be limited by available operating resources. Funding would allow us to address this gap with greater speed, quality, and accountability.

Proposed Project / Program Description
The project will support the activities required to advance {goal}. Key activities may include direct project delivery, equipment or materials, marketing or outreach, staffing or contractor support, training, technology, and evaluation. Final activities will be aligned with the funder's official rules before submission.

Goals, Objectives, and Measurable Outcomes
Our primary goal is to strengthen capacity and produce measurable progress tied to the proposed funding purpose. By the end of the project period, we expect to improve operational efficiency, reach more customers or participants, strengthen service quality, and document outcomes through practical performance indicators.

Use of Funds
The requested grant amount is {amount}. Funds will be allocated toward eligible project costs, including direct project delivery, equipment or materials, staffing or contractor support, marketing or outreach, training, and measurement. Every expense will be connected to project implementation and tracked through appropriate records.

Budget Narrative
The budget reflects a practical, cost-conscious approach to achieving the proposed results. Personnel, contractors, equipment, supplies, technology, outreach, training, and evaluation costs will be used only where they directly support the project goals. Final line items will be confirmed against the official grant requirements before submission.

Sustainability Plan
This funding will help build capacity that can continue beyond the grant period. We will sustain the work through disciplined budgeting, ongoing customer or community engagement, operational improvements, partnerships, and continued pursuit of appropriate funding or revenue opportunities.

Evaluation and Reporting Plan
We will measure progress through both quantitative and qualitative indicators, including services delivered, customer or participant reach, revenue or operational growth, staff capacity, milestone completion, and documentation of outcomes. We will maintain records of grant expenditures and results throughout the project period.

Organizational Strength and Grant Fit
This proposal aligns with {grant_name} because it supports a clear applicant need and a practical plan for measurable results. Our profile appears aligned with the opportunity based on the information available, and we will verify all eligibility requirements, deadlines, allowable costs, and required attachments directly through the official funder before submission.

Required Attachments Checklist
Before submitting, we will confirm the required application form, proposal narrative, project budget, budget narrative, registration or tax documents where applicable, financial statements where requested, leadership or business documentation, and any funder-specific attachments.

Final Review Checklist
Before submission, we will confirm that the proposal directly answers the funder's questions, the project matches the funder's priorities, the amount requested matches the budget, all expenses are eligible, outcomes are measurable, required attachments are included, and the application is submitted before the deadline.

Closing Statement
We respectfully request consideration for {grant_name}. This funding would help us implement a focused plan, strengthen our capacity, and produce meaningful results for our business, customers, and community.
"""

def groq_chat(prompt: str, temperature: float = 0.25) -> str:
    if not settings.groq_api_key or settings.groq_api_key.lower() in {"dummy", "your_groq_key", ""}:
        return "AI provider is not configured yet. A safe fallback draft was created."
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        res = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return res.choices[0].message.content or ""
    except Exception:
        return "AI provider is temporarily unavailable. A safe fallback draft was created."

def ai_json(prompt: str) -> dict:
    text = groq_chat(prompt + "\nReturn valid compact JSON only.")
    try:
        return json.loads(text.strip().strip('`').replace('json\n', '', 1))
    except Exception:
        return {"score": 75, "strengths": ["Complete working draft"], "risks": ["AI review unavailable or returned non-JSON"], "missing_items": ["Verify official funder requirements"], "recommended_fixes": ["Customize with exact documents, dates, and numbers"], "raw": text}

def generate_proposal(org: dict, grant: dict | None, requested_amount: float | None, purpose: str | None) -> str:
    profile_type = (org.get("profile_type") or org.get("org_type") or "organization").lower()
    voice_instruction = "Use first-person singular voice (I/my) from the applicant's point of view." if profile_type in {"individual", "student", "artist", "veteran", "family", "homeowner"} else "Use first-person plural voice (we/our) from the applicant or organization's point of view."
    prompt = f"""
Write a polished, premium, funder-ready grant application narrative from the CLIENT'S point of view.

Critical rules:
- Do NOT mention any platform, AI, automation, agents, software, system, generated by, prepared by, or assisted by.
- Do NOT write as a consultant describing the client from the outside unless required by the section.
- {voice_instruction}
- Make the writing sound like the applicant is directly applying.
- Avoid generic filler. Use concrete, credible, professional language.
- Do not claim guaranteed approval, official eligibility, or exact deadlines unless provided.
- If details are missing, phrase them as items the applicant will confirm, not as system limitations.
- Make the proposal more persuasive, polished, and submission-ready than a basic AI draft.

Required sections for individual profiles:
Applicant Summary, Personal Need, Funding Goal, Use of Funds, Expected Outcome, Eligibility Alignment, Required Documents, Conclusion.

Required sections for business/nonprofit/organization profiles:
Executive Summary, Applicant Overview, Statement of Need / Problem Description, Proposed Project / Program Description, Goals, Objectives, and Measurable Outcomes, Use of Funds, Budget Narrative, Sustainability Plan, Evaluation and Reporting Plan, Organizational Strength and Grant Fit, Required Attachments Checklist, Final Review Checklist, Closing Statement.

Funding profile JSON:
{json.dumps(org, default=str)}

Grant JSON:
{json.dumps(grant or {}, default=str)}

Requested amount:
{requested_amount}

Funding purpose:
{_clean_purpose(purpose) or "Not provided"}
"""
    text = groq_chat(prompt, temperature=0.32)
    if text.startswith("AI provider"):
        return stabilize_sections(_fallback_narrative(org, grant, requested_amount, purpose))
    text = stabilize_sections(text)
    if not is_submission_safe(text):
        text = stabilize_sections(_fallback_narrative(org, grant, requested_amount, purpose))
    return sanitize_proposal_text(text)

def score_proposal(body: str, grant: dict | None = None) -> dict:
    prompt = f"""
Review this grant proposal. Score 0-100 and return JSON with score, strengths, risks, missing_items, and recommended_fixes.
Grant: {json.dumps(grant or {}, default=str)}
Proposal: {body[:12000]}
"""
    data = ai_json(prompt)
    if "score" not in data:
        data["score"] = 75
    return data
