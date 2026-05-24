from app.core.config import settings


def enabled(name: str) -> bool:
    return bool(getattr(settings, name, False))


def require_enabled(name: str) -> None:
    from fastapi import HTTPException
    if not enabled(name):
        raise HTTPException(403, f"{name} is not enabled yet. Add required env vars when your team is ready.")
