from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.models.tables import Notification, UserNotificationSetting, GrantAlert, User, Organization, Grant
from app.services.emailer import send_email
from app.services.grants import match_score, profile_text


def get_or_create_settings(db: Session, user: User) -> UserNotificationSetting:
    row = db.query(UserNotificationSetting).filter(UserNotificationSetting.user_id == user.id).first()
    if row:
        return row
    row = UserNotificationSetting(tenant_id=user.tenant_id, user_id=user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_notification(
    db: Session,
    user: User,
    title: str,
    message: str,
    type: str = "grant_match",
    organization_id: int | None = None,
    grant_id: int | None = None,
    action_url: str | None = None,
    priority: str = "normal",
    send_email_now: bool = True,
) -> Notification:
    settings_row = get_or_create_settings(db, user)
    note = Notification(
        tenant_id=user.tenant_id,
        user_id=user.id,
        organization_id=organization_id,
        grant_id=grant_id,
        type=type,
        title=title,
        message=message,
        action_url=action_url,
        priority=priority,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    if send_email_now and settings_row.email_grant_matches:
        try:
            email_text = message + (f"\n\nOpen: {action_url}" if action_url else "")
            email_html = f"""
            <div style="font-family:Arial,sans-serif;background:#000;color:#f7fff7;padding:28px">
              <div style="max-width:640px;margin:auto;background:#071008;border:1px solid rgba(152,251,152,.28);border-radius:24px;padding:28px">
                <h1 style="color:#98FB98;margin-top:0">{title}</h1>
                <pre style="white-space:pre-wrap;font-family:Arial,sans-serif;line-height:1.6;color:#d9ead9">{message}</pre>
                {f'<p><a href="{action_url}" style="display:inline-block;background:#98FB98;color:#001b06;text-decoration:none;font-weight:800;padding:12px 18px;border-radius:12px">View Funding Opportunity</a></p>' if action_url else ''}
                <p style="color:#8fa18f;font-size:12px;margin-top:24px">You are receiving this because Mogul Grant System found a funding match based on your profile and notification settings.</p>
              </div>
            </div>
            """
            sent = send_email(user.email, title, email_text, email_html)
            note.email_sent = bool(sent)
            db.add(note)
            db.commit()
            db.refresh(note)
        except Exception as exc:
            note.message = note.message + f"\n\nEmail delivery error: {exc}"
            db.add(note)
            db.commit()
            db.refresh(note)
    return note


def notify_user_about_grant(db: Session, user: User, org: Organization, grant: Grant, score: float) -> Notification | None:
    settings_row = get_or_create_settings(db, user)
    if score < float(settings_row.minimum_match_score or 0):
        return None
    try:
        alert = GrantAlert(
            tenant_id=user.tenant_id,
            user_id=user.id,
            organization_id=org.id,
            grant_id=grant.id,
            match_score=score,
        )
        db.add(alert)
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    if not settings_row.platform_grant_matches and not settings_row.email_grant_matches:
        return None
    title = f"New funding match: {grant.title}"
    message = (
        f"Mogul Grant System found a {round(score)}% match for {org.name}.\n\n"
        f"Source: {grant.source}\n"
        f"Category: {grant.category or 'General'}\n"
        f"Deadline: {grant.deadline or 'Varies'}\n"
        f"Eligibility: {(grant.eligibility or 'See official source')[:700]}\n\n"
        "Log in to save it, generate a proposal, or start the application workflow."
    )
    return create_notification(
        db=db,
        user=user,
        title=title,
        message=message,
        type="grant_match",
        organization_id=org.id,
        grant_id=grant.id,
        action_url=grant.application_url,
        priority="high" if score >= 90 else "normal",
        send_email_now=settings_row.email_grant_matches,
    )


def scan_and_notify_for_user(db: Session, user: User, grants: list[Grant]) -> int:
    orgs = db.query(Organization).filter(Organization.tenant_id == user.tenant_id, Organization.owner_user_id == user.id).all()
    sent = 0
    for org in orgs:
        text = profile_text(org, org.funding_goals or org.mission or org.name)
        for grant in grants:
            if grant.audience not in {"all", "individual" if org.profile_type in {"individual", "student", "artist", "veteran", "family", "homeowner"} else "organization"}:
                continue
            score = match_score(grant, text)
            if notify_user_about_grant(db, user, org, grant, score):
                sent += 1
    return sent
