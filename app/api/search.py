from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.services.advanced_search import hybrid_grant_search

router = APIRouter(prefix="/search", tags=["Semantic Search"])

@router.get("/grants")
def search_grants(q: str = Query(..., min_length=2), audience: str = "all", category: str | None = None, db: Session = Depends(get_db), user=Depends(current_user)):
    return {"results": hybrid_grant_search(db, q, audience=audience, category=category, limit=30)}
