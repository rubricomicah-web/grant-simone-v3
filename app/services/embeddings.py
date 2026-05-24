"""Vector-memory foundation.

Deploys safely today with deterministic local vectors. When OPENAI_API_KEY or another
embedding provider is added, replace embed_text() internals without changing routes.
"""
from __future__ import annotations
import hashlib, math
from sqlalchemy.orm import Session
from app.models.tables import Memory

VECTOR_DIM = 64


def embed_text(text: str) -> list[float]:
    text = (text or "").lower().strip()
    if not text:
        return [0.0] * VECTOR_DIM
    buckets = [0.0] * VECTOR_DIM
    for token in text.split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = digest[0] % VECTOR_DIM
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        buckets[idx] += sign
    norm = math.sqrt(sum(x * x for x in buckets)) or 1.0
    return [round(x / norm, 6) for x in buckets]


def similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def remember(db: Session, tenant_id: int, organization_id: int, memory_type: str, content: str, importance: float = 0.5):
    vector = embed_text(content)
    mem = Memory(
        tenant_id=tenant_id,
        organization_id=organization_id,
        memory_type=memory_type,
        content=content,
        importance=importance,
    )
    # Store vector in metadata-like content companion if model lacks vector column.
    # Vector column can be added with pgvector later.
    db.add(mem)
    db.flush()
    return {"memory_id": mem.id, "vector_preview": vector[:6]}


def semantic_recall(db: Session, tenant_id: int, organization_id: int, query: str, limit: int = 5):
    qv = embed_text(query)
    memories = db.query(Memory).filter(Memory.tenant_id == tenant_id, Memory.organization_id == organization_id).all()
    scored = []
    for m in memories:
        mv = embed_text(m.content)
        scored.append((similarity(qv, mv) + float(m.importance or 0) * 0.05, m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": round(score, 4), "memory_id": m.id, "type": m.memory_type, "content": m.content} for score, m in scored[:limit]]
