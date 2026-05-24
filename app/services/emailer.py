import httpx
from app.core.config import settings


def send_email(to_email: str, subject: str, body: str, html: str | None = None) -> bool:
    """Production email sender using Resend.

    Required Railway env vars:
    - RESEND_API_KEY
    - RESEND_FROM_EMAIL, for example: Mogul Grant System <notifications@yourdomain.com>

    Returns False when email is disabled or Resend is not configured, so the app keeps working.
    """
    if not settings.email_notifications_enabled:
        return False
    if not settings.resend_api_key or not settings.resend_from_email:
        return False

    payload = {
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if html:
        payload["html"] = html

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    response = httpx.post(
        "https://api.resend.com/emails",
        json=payload,
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    return True
