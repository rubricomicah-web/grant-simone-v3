
import httpx
from sqlalchemy.orm import Session
from app.services.grants import search_grants_gov, upsert_grant, normalize_state

async def ingest_live_grants(db: Session, query: str = "small business nonprofit education housing benefits", state: str | None = None, limit: int = 25) -> dict:
    state = normalize_state(state)
    """Live ingestion. Never fabricates opportunities and never inserts generic fallback cards.

    Current built-in live source: Grants.gov posted federal opportunities.
    Private/state sources should be added as explicit source adapters only when
    their official source URL/parser is configured.
    """
    inserted = 0
    errors = []
    try:
        for item in await search_grants_gov(query, None, limit):
            item["state"] = "National"
            upsert_grant(db, item)
            inserted += 1
    except Exception as exc:
        errors.append(f"Grants.gov: {exc}")
    return {"ingested": inserted, "errors": errors, "sources": ["Grants.gov"], "note": "No fallback or dummy grants were inserted."}

async def verify_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            res = await client.head(url)
            if res.status_code >= 400:
                res = await client.get(url)
            return res.status_code < 400
    except Exception:
        return False
