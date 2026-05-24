from app.services.dedupe import index_grant
from app.services.deadlines import deadline_status
from datetime import datetime, timezone
import hashlib, httpx
from sqlalchemy.orm import Session
from app.models.tables import Grant, Organization
from app.services.curated_sources import CURATED_VERIFIED_GRANTS
from app.services.funding_engine import search_verified_sources, BusinessAwareMatcher, FundingRecommendationEngine
from app.services.profile_intelligence import organization_profile_text, search_prompt_from_profile

GRANTS_GOV = "https://api.grants.gov/v1/api/search2"

def confidence(grant: dict) -> float:
    score = 58
    if grant.get("application_url"): score += 10
    if grant.get("deadline"): score += 8
    if grant.get("description") and len(grant["description"]) > 120: score += 8
    if grant.get("eligibility"): score += 6
    if grant.get("source") in {"Grants.gov", "SBA", "USDA", "NSF", "USA.gov", "Benefits.gov", "CareerOneStop", "StudentAid.gov", "WomensNet", "IFundWomen", "Hello Alice", "FedEx", "Visa", "MBDA", "Verizon", "Cartier Women's Initiative", "NASE"}: score += 10
    return min(score, 98)

def upsert_grant(db: Session, item: dict) -> Grant:
    source = item.get("source", "manual")
    source_id = item.get("source_id") or hashlib.sha256((source + item.get("title", "") + item.get("application_url", "")).encode()).hexdigest()[:24]
    row = db.query(Grant).filter(Grant.source == source, Grant.source_id == source_id).first()
    if not row:
        row = Grant(source=source, source_id=source_id, title=item["title"], description=item.get("description", ""))
        db.add(row)
    for key in ["title", "description", "eligibility", "audience", "category", "amount_min", "amount_max", "deadline", "state", "application_url"]:
        if key in item:
            value = normalize_state(item[key]) if key == "state" else item[key]
            setattr(row, key, value)
    row.verified = bool(item.get("verified", source != "web"))
    row.confidence_score = item.get("confidence_score") or confidence(item)
    row.last_checked_at = datetime.now(timezone.utc)
    row.raw_json = item.get("raw_json", item)
    db.commit(); db.refresh(row)
    try:
        index_grant(db, row)
    except Exception:
        pass
    return row


async def search_grants_gov(query: str, state: str | None, limit: int = 10) -> list[dict]:
    """Live Grants.gov search with MCP-style async retry/backoff and normalization."""
    return await search_verified_sources(query, state=state, audience="organization", category="federal", limit=limit)



def _tokens(text: str) -> set[str]:
    stop = {
        "grant", "grants", "funding", "assistance", "program", "programs", "small", "business",
        "organization", "individual", "need", "needs", "for", "and", "the", "with", "from", "support",
        "help", "money", "apply", "application", "startup", "nonprofit"
    }
    cleaned = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in (text or ''))
    return {w for w in cleaned.split() if len(w) > 2 and w not in stop}

INDUSTRY_SYNONYMS = {
    "beauty": {"beauty", "salon", "cosmetology", "barber", "spa", "esthetician", "hair", "nail", "skincare", "wellness"},
    "restaurant": {"restaurant", "food", "cafe", "coffee", "bakery", "catering", "hospitality", "bar", "foodtruck", "food truck", "culinary"},
    "retail_ecommerce": {"retail", "store", "boutique", "ecommerce", "e-commerce", "shopify", "online store", "merchandise", "inventory", "fashion", "apparel"},
    "trucking_logistics": {"trucking", "truck", "fleet", "logistics", "transportation", "delivery", "freight", "cdl", "supply chain", "courier"},
    "construction_contractors": {"construction", "contractor", "contractors", "hvac", "plumbing", "electrician", "roofing", "renovation", "builder", "trade"},
    "real_estate": {"real estate", "property", "landlord", "developer", "housing", "rental", "mortgage", "rehab", "community development"},
    "manufacturing": {"manufacturing", "manufacturer", "production", "factory", "industrial", "machinery", "fabrication", "supply"},
    "technology": {"technology", "tech", "software", "ai", "cyber", "digital", "innovation", "fintech", "payments", "saas", "app", "data"},
    "healthcare": {"health", "healthcare", "medical", "clinic", "mental", "behavioral", "wellness", "therapy", "dental", "care"},
    "education_childcare": {"education", "student", "school", "college", "tuition", "training", "scholarship", "childcare", "daycare", "tutoring", "youth"},
    "agriculture": {"farm", "farmer", "agriculture", "agricultural", "rural", "food", "producer", "value-added", "ranch"},
    "arts_creators": {"art", "artist", "arts", "creative", "creator", "music", "film", "media", "content", "design"},
    "fitness_wellness": {"fitness", "gym", "studio", "yoga", "pilates", "training", "wellness", "sports"},
    "professional_services": {"consulting", "agency", "accounting", "legal", "bookkeeping", "marketing agency", "professional services", "coaching"},
    "tourism_hospitality": {"tourism", "hotel", "lodging", "travel", "hospitality", "restaurant", "event", "venue"},
    "nonprofit_community": {"nonprofit", "community", "social services", "foundation", "charity", "youth", "equity", "housing", "food insecurity"},
    "clean_energy": {"energy", "solar", "clean energy", "climate", "sustainability", "efficiency", "green", "ev", "electric vehicle"},
}

NEED_SYNONYMS = {
    "equipment": {"equipment", "tools", "machinery", "supplies", "inventory", "technology", "hardware", "vehicle", "vehicles", "fleet"},
    "expansion": {"expansion", "grow", "growth", "scale", "renovation", "buildout", "capacity", "new location", "launch"},
    "marketing": {"marketing", "advertising", "brand", "branding", "website", "digital", "outreach", "social media", "customer acquisition"},
    "working_capital": {"working capital", "cash flow", "operations", "operating", "rent", "lease", "utilities", "payroll", "wages"},
    "payroll_hiring": {"payroll", "wages", "salary", "staff", "workforce", "hiring", "jobs", "contractor", "training"},
    "startup_capital": {"startup", "start up", "launch", "seed", "startup capital", "prototype", "mvp", "founder"},
    "technology": {"software", "technology", "digital", "automation", "cybersecurity", "pos", "crm", "website", "app"},
    "research_development": {"research", "development", "r&d", "prototype", "clinical", "innovation", "commercialization", "sbir", "sttr"},
    "export_growth": {"export", "international", "trade", "global", "market expansion"},
    "emergency": {"emergency", "disaster", "relief", "hardship", "crisis"},
    "education": {"education", "tuition", "training", "scholarship", "school", "college", "credential"},
    "housing": {"housing", "rent", "mortgage", "utility", "utilities", "home", "shelter"},
    "community_impact": {"community", "impact", "equity", "underserved", "jobs", "access", "health", "education"},
}


SPECIAL_CATEGORY_TAGS = {
    "private": {"private", "private grant", "private marketplace", "private foundation", "membership grant"},
    "corporate": {"corporate", "corporate private", "corporate competition", "contest", "competition"},
    "women": {"women", "women owned", "women led", "founders"},
    "minority": {"minority owned", "minority business", "minority"},
    "digital": {"digital transformation", "digital", "marketing", "website", "technology"},
}

def _category_matches(item: dict, category: str | None) -> bool:
    if not category or category == "all":
        return True
    item_category = (item.get("category") or "").lower()
    if item_category == category:
        return True
    tags = _flatten_raw_tags(item.get("raw_json")).lower() if "_flatten_raw_tags" in globals() else ""
    special = SPECIAL_CATEGORY_TAGS.get(category, set())
    if special and any(t in tags for t in special):
        return True
    return False


US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "PR": "Puerto Rico", "GU": "Guam", "VI": "U.S. Virgin Islands", "AS": "American Samoa",
    "MP": "Northern Mariana Islands"
}
US_STATE_NAMES = {v.lower(): v for v in US_STATES.values()}
US_STATE_ALIASES = {k.lower(): v for k, v in US_STATES.items()} | US_STATE_NAMES | {
    "usa": "National", "us": "National", "u.s.": "National", "all usa": "National",
    "nationwide": "National", "national": "National", "federal": "National", "all states": "National",
    "washington dc": "District of Columbia", "d.c.": "District of Columbia", "dc": "District of Columbia",
    "virgin islands": "U.S. Virgin Islands", "us virgin islands": "U.S. Virgin Islands"
}
NATIONAL_STATES = {"National", "Federal", "Nationwide", "All USA", "All States", None, ""}

def normalize_state(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    key = text.lower().replace("_", " ").replace("-", " ")
    key = " ".join(key.split())
    return US_STATE_ALIASES.get(key, text)

def state_matches(grant_state: str | None, requested_state: str | None) -> bool:
    """Support all USA states and territories.

    Federal/national grants remain visible for every state. State-specific grants
    only appear when their state matches the selected state. This prevents a
    California-only result from being shown to a Texas user, while still allowing
    national/federal grants to show for all users.
    """
    req = normalize_state(requested_state)
    gs = normalize_state(grant_state)
    if not req or req in NATIONAL_STATES:
        return True
    if gs in NATIONAL_STATES:
        return True
    parts = [normalize_state(x) for x in str(gs or "").replace(";", ",").split(",")]
    return req in parts


def _expanded_query_terms(query: str) -> set[str]:
    terms = _tokens(query)
    lower = (query or '').lower()
    for group in list(INDUSTRY_SYNONYMS.values()) + list(NEED_SYNONYMS.values()):
        if terms & group or any(phrase in lower for phrase in group):
            terms |= group
    return terms

def _flatten_raw_tags(raw) -> str:
    if not isinstance(raw, dict):
        return ""
    parts = []
    for key in ["funding_type", "source_kind", "status", "amount_display", "curated_as_of"]:
        if raw.get(key):
            parts.append(str(raw.get(key)))
    for key in ["industries", "needs_supported", "demographics", "organization_types", "states"]:
        value = raw.get(key)
        if isinstance(value, list):
            parts.extend(str(x) for x in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts)

def _grant_text_dict(item: dict) -> str:
    return " ".join([
        " ".join(str(item.get(k) or '') for k in ["title", "description", "eligibility", "category", "audience", "source"]),
        _flatten_raw_tags(item.get("raw_json")),
    ]).lower()


def _raw_list(item: dict, key: str) -> set[str]:
    raw = item.get("raw_json") if isinstance(item.get("raw_json"), dict) else {}
    value = raw.get(key, [])
    if isinstance(value, str):
        value = [value]
    return {str(x).lower().replace("_", " ") for x in (value or [])}

def _query_groups(query: str) -> tuple[set[str], set[str]]:
    terms = _expanded_query_terms(query)
    industries = set()
    needs = set()
    for name, words in INDUSTRY_SYNONYMS.items():
        if terms & words:
            industries.add(name)
            industries |= words
    for name, words in NEED_SYNONYMS.items():
        if terms & words:
            needs.add(name)
            needs |= words
    return industries, needs

def match_details(item: dict, query: str, state: str | None = None) -> dict:
    """Explain matching without claiming a broad source is industry-exclusive."""
    text = _grant_text_dict(item)
    terms = _expanded_query_terms(query)
    hits = sorted({t for t in terms if t in text})[:12]
    industries, needs = _query_groups(query)
    raw_industries = _raw_list(item, "industries")
    raw_needs = _raw_list(item, "needs_supported")
    raw_demo = _raw_list(item, "demographics")
    industry_hits = sorted((industries & raw_industries) or ({t for t in industries if t in text}))[:8]
    need_hits = sorted((needs & raw_needs) or ({t for t in needs if t in text}))[:8]
    reason_bits = []
    if normalize_state(state) and normalize_state(state) not in NATIONAL_STATES:
        reason_bits.append(f"Available for {normalize_state(state)} because this opportunity is {item.get('state') or 'National'}")
    if industry_hits:
        reason_bits.append("Industry fit: " + ", ".join(industry_hits[:4]))
    if need_hits:
        reason_bits.append("Need fit: " + ", ".join(need_hits[:4]))
    if raw_demo:
        reason_bits.append("Eligibility tags: " + ", ".join(sorted(raw_demo)[:4]))
    if not reason_bits:
        reason_bits.append("Verified source match based on title, description, eligibility, and tags")
    return {"matched_terms": hits, "industry_hits": industry_hits, "need_hits": need_hits, "reason": "; ".join(reason_bits)}

def is_relevant_item(item: dict, query: str, audience: str = "all", category: str | None = None, state: str | None = None) -> bool:
    """Strict relevance guard. This prevents generic grants from showing for specific searches.

    We only show verified opportunities that have enough textual overlap with the user's actual need.
    If a user searches 'beauty salon equipment California', generic unrelated federal grants are filtered out.
    """
    if not item.get("verified", True):
        return False
    if audience != "all" and item.get("audience", "all") not in {audience, "all"}:
        return False
    if not _category_matches(item, category):
        return False
    if not state_matches(item.get("state"), state):
        return False
    terms = _expanded_query_terms(query)
    if not terms:
        return True
    text = _grant_text_dict(item)
    hits = {t for t in terms if t in text}
    industries, needs = _query_groups(query)
    raw_industries = _raw_list(item, "industries")
    raw_needs = _raw_list(item, "needs_supported")
    industry_hit = bool(industries and (industries & raw_industries or any(t in text for t in industries)))
    need_hit = bool(needs and (needs & raw_needs or any(t in text for t in needs)))

    # If the user has a clear industry/need such as beauty salon equipment,
    # require a real tag/text match. Broad unrelated Grants.gov records are blocked.
    if industries and needs:
        return industry_hit and need_hit
    if industries:
        return industry_hit
    if needs:
        return need_hit
    if len(terms) >= 4:
        return len(hits) >= 2
    return len(hits) >= 1

def is_relevant_grant(grant: Grant, query: str, audience: str = "all", category: str | None = None, state: str | None = None) -> bool:
    return is_relevant_item({
        "title": grant.title,
        "description": grant.description,
        "eligibility": grant.eligibility,
        "audience": grant.audience,
        "category": grant.category,
        "state": grant.state,
        "source": grant.source,
        "verified": grant.verified,
        "raw_json": grant.raw_json or {},
    }, query, audience, category, state)

# Intentionally no fallback_grants function.
# Mogul Grant System must never fabricate or pad results with generic source-directory cards.
# If no verified relevant funding opportunity is found, the API returns an empty list plus a clear message.



def ensure_curated_verified_grants(db: Session) -> int:
    """Upsert real curated national/private/corporate grants from the team list.

    These records are not dummy grants. They are a verified source base layer
    used alongside live ingestion.
    """
    count = 0
    for item in CURATED_VERIFIED_GRANTS:
        upsert_grant(db, item)
        count += 1
    return count

async def discover(db: Session, query: str, state: str | None, limit: int = 10, audience: str = "all", category: str | None = None) -> list[Grant]:
    query = (query or "").strip()
    state = normalize_state(state)
    rows: list[Grant] = []

    # 0) Maintain a real curated national funding base layer.
    # These are team-provided verified source records, not dummy/fake fallback grants.
    ensure_curated_verified_grants(db)

    # 1) Search verified records already in the database.
    dbq = db.query(Grant).filter(Grant.verified == True)
    if audience != "all":
        dbq = dbq.filter(Grant.audience.in_([audience, "all"]))
    if category and category != "all" and category not in SPECIAL_CATEGORY_TAGS:
        dbq = dbq.filter(Grant.category == category)
    existing = dbq.order_by(Grant.last_checked_at.desc()).limit(300).all()
    for g in existing:
        if is_relevant_grant(g, query, audience, category, state):
            rows.append(g)

    # 2) Live verified source search with async retry/backoff and normalization.
    # The current live adapter is Grants.gov. The funding engine is structured for
    # additional verified SBA/state/private/corporate adapters without changing this route.
    should_live_search = audience in {"all", "organization"}
    if should_live_search and len(rows) < limit:
        for item in await search_verified_sources(query, state=state, audience=audience, category=category, limit=max(10, limit * 2)):
            item["state"] = item.get("state") or "National"
            if not is_relevant_item(item, query, audience, category, state):
                continue
            rows.append(upsert_grant(db, item))

    # 3) Deduplicate and rank.
    seen: set[int] = set()
    clean: list[Grant] = []
    for g in rows:
        if g.id in seen:
            continue
        seen.add(g.id)
        clean.append(g)
    clean.sort(key=lambda g: (match_score(g, query), g.confidence_score or 0), reverse=True)
    return clean[:limit]

def profile_text(profile: Organization | None, fallback: str = "") -> str:
    if not profile:
        return fallback
    return organization_profile_text(profile, fallback)

def match_score(grant: Grant, org_text: str) -> int:
    item = {
        "title": grant.title, "description": grant.description, "eligibility": grant.eligibility,
        "audience": grant.audience, "category": grant.category, "state": grant.state,
        "source": grant.source, "raw_json": grant.raw_json or {},
    }
    text = _grant_text_dict(item)
    words = _expanded_query_terms(org_text)
    hits = sum(1 for w in words if w in text)
    industries, needs = _query_groups(org_text)
    raw_industries = _raw_list(item, "industries")
    raw_needs = _raw_list(item, "needs_supported")
    base = int((grant.confidence_score or 70) * 0.45) + min(hits * 5, 35)
    if industries and (industries & raw_industries):
        base += 18
    if needs and (needs & raw_needs):
        base += 16
    if grant.state in {"National", "Federal", "Nationwide", "All USA", None}:
        base += 2
    return max(0, min(base, 99))
