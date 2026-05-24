"""Universal funding engine for Mogul Grant System.

This module adapts the useful MCP concepts into Mogul's product architecture:
- async funding fetch architecture
- retry/backoff request handling
- opportunity normalization
- business-aware matching
- cleaner recommendation logic
- multi-source preparation layer

It intentionally does not fabricate results. If a source is unavailable, the
engine returns an empty list and the UI can explain that no verified matches
were found.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

import httpx

from app.services.structured_logging import timed_external_call, log_business_match

logger = logging.getLogger("mogul.funding")


@dataclass(slots=True)
class FundingOpportunity:
    source: str
    source_id: str
    title: str
    description: str = ""
    eligibility: str | None = None
    audience: str = "organization"
    category: str = "business"
    amount_min: float | None = None
    amount_max: float | None = None
    deadline: str | None = None
    state: str = "National"
    application_url: str | None = None
    verified: bool = True
    confidence_score: int = 80
    raw_json: dict[str, Any] = field(default_factory=dict)

    def to_grant_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "description": self.description,
            "eligibility": self.eligibility,
            "audience": self.audience,
            "category": self.category,
            "amount_min": self.amount_min,
            "amount_max": self.amount_max,
            "deadline": self.deadline,
            "state": self.state,
            "application_url": self.application_url,
            "verified": self.verified,
            "confidence_score": self.confidence_score,
            "raw_json": self.raw_json,
        }


class AsyncFundingClient:
    """Small async HTTP client with MCP-style retry/backoff observability."""

    def __init__(self, timeout: float = 14.0, max_retries: int = 4) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "MogulGrantSystem/1.0 (+funding-intelligence)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def request_json(self, method: str, url: str, *, service: str, **kwargs) -> dict[str, Any]:
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            last_error: Exception | None = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    with timed_external_call(service, attempt=attempt, url=url):
                        response = await client.request(method, url, **kwargs)
                        if response.status_code == 429 or response.status_code >= 500:
                            if attempt < self.max_retries:
                                await asyncio.sleep(min(2 ** (attempt - 1), 8))
                                continue
                        response.raise_for_status()
                        return response.json()
                except Exception as exc:  # noqa: BLE001 - log and retry safely
                    last_error = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(2 ** (attempt - 1), 8))
                        continue
            logger.warning("source_unavailable service=%s url=%s error=%s", service, url, last_error)
            return {}


class OpportunityNormalizer:
    """Convert source-specific payloads into Mogul's canonical opportunity model."""

    @staticmethod
    def _stable_id(source: str, *parts: str) -> str:
        raw = "|".join([source, *[p or "" for p in parts]])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _amount(value: Any) -> float | None:
        if value in (None, "", "Not specified"):
            return None
        try:
            return float(str(value).replace("$", "").replace(",", ""))
        except Exception:
            return None

    @classmethod
    def grants_gov(cls, hit: dict[str, Any]) -> FundingOpportunity:
        title = hit.get("title") or hit.get("opportunityTitle") or "Federal funding opportunity"
        opp_id = str(hit.get("id") or hit.get("number") or hit.get("opportunityNumber") or cls._stable_id("Grants.gov", title))
        description = hit.get("synopsis") or hit.get("description") or hit.get("agencyName") or "Federal funding opportunity from Grants.gov."
        category = (hit.get("categoryOfFundingActivity") or hit.get("category") or "federal").lower()
        return FundingOpportunity(
            source="Grants.gov",
            source_id=opp_id,
            title=title,
            description=str(description)[:1200],
            eligibility=hit.get("applicantEligibilityDesc") or hit.get("eligibility"),
            audience="organization",
            category="federal" if "federal" not in category else category,
            amount_min=cls._amount(hit.get("awardFloor")),
            amount_max=cls._amount(hit.get("awardCeiling")),
            deadline=hit.get("closeDate") or hit.get("closeDateStr"),
            state="National",
            application_url=f"https://www.grants.gov/search-results-detail/{opp_id}",
            verified=True,
            confidence_score=88,
            raw_json={**hit, "normalized_by": "mogul_funding_engine", "source_kind": "federal"},
        )

    @classmethod
    def generic_verified(cls, source: str, item: dict[str, Any]) -> FundingOpportunity:
        title = item.get("title") or item.get("name") or "Verified funding opportunity"
        source_id = str(item.get("source_id") or item.get("id") or cls._stable_id(source, title, item.get("application_url") or item.get("url") or ""))
        return FundingOpportunity(
            source=source,
            source_id=source_id,
            title=title,
            description=item.get("description") or item.get("summary") or "Verified funding opportunity.",
            eligibility=item.get("eligibility"),
            audience=item.get("audience") or "organization",
            category=item.get("category") or "business",
            amount_min=cls._amount(item.get("amount_min")),
            amount_max=cls._amount(item.get("amount_max")),
            deadline=item.get("deadline"),
            state=item.get("state") or "National",
            application_url=item.get("application_url") or item.get("url"),
            verified=bool(item.get("verified", True)),
            confidence_score=int(item.get("confidence_score") or 82),
            raw_json={**item, "normalized_by": "mogul_funding_engine"},
        )


class BusinessAwareMatcher:
    """Rank opportunities using business profile context instead of generic keyword search."""

    INDUSTRY_WORDS = {
        "restaurant": {"restaurant", "cafe", "coffee", "bakery", "food", "hospitality", "culinary", "catering"},
        "technology": {"technology", "software", "ai", "saas", "app", "cyber", "fintech", "innovation", "digital"},
        "retail": {"retail", "store", "boutique", "ecommerce", "shop", "inventory", "fashion", "apparel"},
        "trucking": {"truck", "trucking", "fleet", "logistics", "freight", "delivery", "transportation", "cdl"},
        "healthcare": {"health", "healthcare", "clinic", "medical", "mental", "therapy", "dental", "care"},
        "construction": {"construction", "contractor", "hvac", "plumbing", "electrical", "roofing", "trade"},
        "beauty": {"beauty", "salon", "barber", "spa", "cosmetology", "hair", "nail", "skincare"},
        "nonprofit": {"nonprofit", "community", "foundation", "charity", "social", "youth", "equity"},
        "education": {"education", "school", "student", "training", "childcare", "daycare", "tuition"},
        "manufacturing": {"manufacturing", "factory", "production", "machinery", "industrial", "fabrication"},
    }
    NEED_WORDS = {
        "equipment": {"equipment", "tools", "machinery", "supplies", "inventory", "vehicle", "fleet"},
        "expansion": {"expansion", "growth", "scale", "capacity", "renovation", "buildout", "new location"},
        "marketing": {"marketing", "advertising", "website", "brand", "branding", "outreach", "digital"},
        "workforce": {"hiring", "payroll", "staff", "training", "jobs", "workforce", "contractor"},
        "working_capital": {"working capital", "cash flow", "operations", "rent", "lease", "utilities"},
        "innovation": {"research", "development", "prototype", "commercialization", "innovation", "sbir", "sttr"},
    }

    @staticmethod
    def tokens(text: str) -> set[str]:
        cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text or "")
        return {w for w in cleaned.split() if len(w) > 2}

    @classmethod
    def profile_keywords(cls, profile_text: str) -> dict[str, set[str]]:
        lower = (profile_text or "").lower()
        industries: set[str] = set()
        needs: set[str] = set()
        for label, words in cls.INDUSTRY_WORDS.items():
            if any(w in lower for w in words):
                industries.add(label)
                industries |= words
        for label, words in cls.NEED_WORDS.items():
            if any(w in lower for w in words):
                needs.add(label)
                needs |= words
        return {"industries": industries, "needs": needs, "tokens": cls.tokens(lower)}

    @classmethod
    def score(cls, opportunity: FundingOpportunity | dict[str, Any], profile_text: str) -> tuple[int, list[str]]:
        if isinstance(opportunity, FundingOpportunity):
            item = opportunity.to_grant_dict()
        else:
            item = opportunity
        raw = item.get("raw_json") or {}
        text = " ".join(str(item.get(k) or "") for k in ["title", "description", "eligibility", "category", "audience", "source"]).lower()
        for key in ["industries", "needs_supported", "demographics", "organization_types"]:
            val = raw.get(key) if isinstance(raw, dict) else None
            if isinstance(val, list):
                text += " " + " ".join(str(v).lower() for v in val)
        profile = cls.profile_keywords(profile_text)
        score = int(item.get("confidence_score") or 70)
        reasons: list[str] = []
        industry_hits = sorted({w for w in profile["industries"] if w in text})[:5]
        need_hits = sorted({w for w in profile["needs"] if w in text})[:5]
        token_hits = sorted({w for w in profile["tokens"] if w in text})[:5]
        if industry_hits:
            score += 18
            reasons.append("Industry fit: " + ", ".join(industry_hits[:3]))
        if need_hits:
            score += 14
            reasons.append("Funding need fit: " + ", ".join(need_hits[:3]))
        if token_hits:
            score += min(10, len(token_hits) * 2)
        if item.get("application_url"):
            score += 3
        if item.get("deadline"):
            score += 2
        if not reasons:
            reasons.append("Verified source match based on profile and opportunity text")
        final = max(0, min(score, 99))
        log_business_match(str(item.get("title") or "Opportunity"), final, reasons)
        return final, reasons


class FundingRecommendationEngine:
    """Clean client-facing recommendation layer."""

    @staticmethod
    def recommendation(score: int, reasons: list[str]) -> dict[str, Any]:
        if score >= 90:
            label = "Strong fit"
            action = "Prepare application package"
        elif score >= 75:
            label = "Good fit"
            action = "Review eligibility and prepare draft"
        elif score >= 60:
            label = "Possible fit"
            action = "Review official rules before drafting"
        else:
            label = "Low fit"
            action = "Use only if eligibility is confirmed"
        return {"label": label, "next_action": action, "reasons": reasons[:4]}


class MultiSourceFundingEngine:
    """Prepared multi-source engine.

    Grants.gov is live. Private/corporate/state sources are intentionally
    represented as source adapters so they can be connected with real APIs,
    approved scrapers, or curated feeds later without changing app routes.
    """

    GRANTS_GOV_V1 = "https://api.grants.gov/v1/api/search2"
    GRANTS_GOV_LEGACY = "https://www.grants.gov/grantsws/rest/opportunities/search/"

    SOURCE_REGISTRY = {
        "grants.gov": {"live": True, "kind": "federal"},
        "sba": {"live": False, "kind": "public"},
        "sbir": {"live": False, "kind": "federal"},
        "state_city": {"live": False, "kind": "state_local"},
        "corporate": {"live": False, "kind": "corporate"},
        "private_foundations": {"live": False, "kind": "private"},
        "accelerators": {"live": False, "kind": "accelerator"},
    }

    def __init__(self) -> None:
        self.client = AsyncFundingClient()
        self.normalizer = OpportunityNormalizer()

    async def search_grants_gov(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        payload = {"keyword": query, "oppStatuses": "posted", "rows": max(10, limit)}
        data = await self.client.request_json("POST", self.GRANTS_GOV_V1, service="grants.gov", json=payload)
        hits = data.get("data", {}).get("oppHits", []) or data.get("oppHits", []) or []
        if not hits:
            params = {"keyword": query, "sortBy": "closeDate", "sortOrder": "ASC", "rows": max(10, limit), "startRecordNum": 0}
            data = await self.client.request_json("GET", self.GRANTS_GOV_LEGACY, service="grants.gov_legacy", params=params)
            hits = data.get("oppHits", []) or []
        normalized = [self.normalizer.grants_gov(hit).to_grant_dict() for hit in hits[:limit]]
        return self.dedupe(normalized)

    async def search_all_enabled(self, query: str, *, state: str | None = None, audience: str = "all", category: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        # Current live source. Registry keeps architecture ready for SBA/state/private adapters.
        results = await self.search_grants_gov(query, limit=limit)
        return self.dedupe(results)[:limit]

    @staticmethod
    def dedupe(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        out: list[dict[str, Any]] = []
        for item in items:
            key = (str(item.get("source") or ""), str(item.get("source_id") or item.get("title") or ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out


async def search_verified_sources(query: str, *, state: str | None = None, audience: str = "all", category: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    engine = MultiSourceFundingEngine()
    return await engine.search_all_enabled(query, state=state, audience=audience, category=category, limit=limit)
