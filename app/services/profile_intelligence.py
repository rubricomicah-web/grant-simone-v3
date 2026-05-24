"""Organization profile intelligence for business-aware funding matching."""
from __future__ import annotations

from typing import Any

INDUSTRY_PROMPTS = {
    "restaurant": "food service, cafe, restaurant, hospitality, equipment, local business, marketing",
    "technology": "technology, software, AI, innovation, accelerator, SBIR, commercialization",
    "retail": "retail, ecommerce, inventory, storefront, marketing, customer acquisition",
    "trucking": "transportation, fleet, logistics, vehicle, workforce, CDL, supply chain",
    "healthcare": "healthcare, clinic, patient access, care delivery, wellness, workforce",
    "construction": "construction, contractor, tools, equipment, workforce, trade services",
    "beauty": "beauty, salon, spa, cosmetology, equipment, storefront, women-owned business",
    "nonprofit": "community impact, foundation grants, program support, outcomes, underserved populations",
    "education": "education, training, students, childcare, youth, scholarships, workforce development",
}

def infer_industry(text: str) -> str:
    lower = (text or "").lower()
    for industry, words in INDUSTRY_PROMPTS.items():
        if any(w in lower for w in words.replace(",", "").split()):
            return industry
    return "general_business"

def organization_profile_text(org: Any, fallback: str = "") -> str:
    fields = []
    for attr in ["name", "profile_type", "org_type", "city", "state", "county", "mission", "funding_goals", "education_level", "employment_status"]:
        value = getattr(org, attr, None) if not isinstance(org, dict) else org.get(attr)
        if value:
            fields.append(str(value))
    tags = getattr(org, "eligibility_tags", None) if not isinstance(org, dict) else org.get("eligibility_tags")
    if tags:
        fields.extend(str(t) for t in tags)
    if fallback:
        fields.append(fallback)
    text = " ".join(fields)
    industry = infer_industry(text)
    if industry in INDUSTRY_PROMPTS:
        text += " " + INDUSTRY_PROMPTS[industry]
    return text.strip()

def search_prompt_from_profile(org: Any, fallback: str = "") -> str:
    text = organization_profile_text(org, fallback)
    industry = infer_industry(text)
    if industry in INDUSTRY_PROMPTS:
        return f"{text} {INDUSTRY_PROMPTS[industry]} funding opportunities"
    return f"{text or fallback} business funding opportunities"
