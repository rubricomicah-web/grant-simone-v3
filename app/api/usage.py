from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user
from app.schemas.api import UsageRecordRequest
from app.services.plans import usage_summary, check_and_record_usage

router = APIRouter(prefix="/usage", tags=["Usage"])

@router.get("/me")
def my_usage(db: Session = Depends(get_db), user = Depends(current_user)):
    return usage_summary(db, user)

@router.post("/record")
def record_usage(payload: UsageRecordRequest, db: Session = Depends(get_db), user = Depends(current_user)):
    for _ in range(max(1, payload.quantity)):
        check_and_record_usage(db, user, payload.event_type, payload.metadata_json)
    return usage_summary(db, user)
