from sqlalchemy.orm import Session
from app.models.tables import AuditLog

def audit(db: Session, action: str, tenant_id: int | None = None, user_id: int | None = None, details: dict | None = None):
    row = AuditLog(action=action, tenant_id=tenant_id, user_id=user_id, details_json=details or {})
    db.add(row)
    db.commit()
