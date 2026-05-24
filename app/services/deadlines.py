from datetime import datetime, timezone


def deadline_status(deadline: str | None) -> dict:
    if not deadline:
        return {"status": "rolling_or_unknown", "days_left": None, "urgency": "normal"}
    raw = str(deadline).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days = (dt - datetime.now(timezone.utc)).days
            if days < 0:
                return {"status": "expired", "days_left": days, "urgency": "expired"}
            if days <= 7:
                return {"status": "open", "days_left": days, "urgency": "urgent"}
            if days <= 30:
                return {"status": "open", "days_left": days, "urgency": "soon"}
            return {"status": "open", "days_left": days, "urgency": "normal"}
        except Exception:
            pass
    return {"status": "unknown_format", "days_left": None, "urgency": "normal"}
