from __future__ import annotations
from sqlalchemy.orm import Session
from app.models.tables import Grant
from app.services.embeddings import embed_text, similarity


def hybrid_grant_search(db: Session, query: str, audience: str = "all", category: str | None = None, limit: int = 20):
    qv = embed_text(query)
    rows = db.query(Grant).all()
    results = []
    words = {w.lower() for w in (query or "").split() if len(w) > 2}
    for g in rows:
        if audience != "all" and g.audience not in {"all", audience}:
            continue
        if category and (g.category or "").lower() != category.lower():
            continue
        hay = " ".join([g.title or "", g.description or "", g.eligibility or "", g.category or ""]).lower()
        keyword_score = sum(1 for w in words if w in hay) / max(len(words), 1)
        vector_score = similarity(qv, embed_text(hay[:4000]))
        verified_bonus = 0.15 if g.verified else 0.0
        score = max(0.0, min(1.0, keyword_score * 0.6 + vector_score * 0.3 + verified_bonus))
        results.append((score, g))
    results.sort(key=lambda x: x[0], reverse=True)
    return [{
        "id": g.id,
        "grantName": g.title,
        "description": g.description,
        "eligibility": g.eligibility,
        "source": g.source,
        "applicationUrl": g.application_url,
        "category": g.category,
        "deadline": g.deadline,
        "verified": g.verified,
        "matchScore": int(round(score * 100)),
    } for score, g in results[:limit]]
