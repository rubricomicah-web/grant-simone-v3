from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_paid_user
from app.models.tables import Notification, UserNotificationSetting, Grant
from app.schemas.api import NotificationSettingsUpdate
from app.services.notifications import get_or_create_settings, scan_and_notify_for_user
from app.services.serialize import model_to_dict

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("")
def list_notifications(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100).all()
    unread = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()  # noqa: E712
    return {"unread": unread, "notifications": [model_to_dict(r) for r in rows]}

@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    row = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not row:
        raise HTTPException(404, "Notification not found")
    row.is_read = True
    db.add(row); db.commit(); db.refresh(row)
    return model_to_dict(row)

@router.get("/settings")
def notification_settings(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    return model_to_dict(get_or_create_settings(db, user))

@router.patch("/settings")
def update_notification_settings(payload: NotificationSettingsUpdate, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    row = get_or_create_settings(db, user)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.add(row); db.commit(); db.refresh(row)
    return model_to_dict(row)

@router.post("/scan-now")
def scan_now(db: Session = Depends(get_db), user = Depends(require_paid_user)):
    grants = db.query(Grant).filter(Grant.verified == True).order_by(Grant.last_checked_at.desc()).limit(80).all()  # noqa: E712
    count = scan_and_notify_for_user(db, user, grants)
    return {"created_notifications": count}
