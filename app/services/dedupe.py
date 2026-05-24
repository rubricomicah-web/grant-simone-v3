import re
from sqlalchemy.orm import Session
from app.models.tables import Grant, GrantCanonical


def canonical_key(title: str, source: str | None, url: str | None) -> str:
    base = url or f"{source or ''}:{title}"
    base = base.lower().strip()
    base = re.sub(r"https?://(www\.)?", "", base)
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base[:480]


def index_grant(db: Session, grant: Grant) -> str:
    key = canonical_key(grant.title, grant.source, grant.source_url)
    row = db.query(GrantCanonical).filter(GrantCanonical.canonical_key == key).first()
    if not row:
        row = GrantCanonical(canonical_key=key, primary_grant_id=grant.id, duplicate_grant_ids=[])
    elif row.primary_grant_id != grant.id and grant.id not in (row.duplicate_grant_ids or []):
        ids = list(row.duplicate_grant_ids or [])
        ids.append(grant.id)
        row.duplicate_grant_ids = ids
    db.add(row); db.commit()
    return key
