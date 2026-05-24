from datetime import datetime

def model_to_dict(obj, exclude: set[str] | None = None):
    exclude = exclude or set()
    data = {}
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        data[col.name] = val
    return data
