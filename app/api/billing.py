from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import current_user
from app.models.tables import Subscription, User
from app.schemas.api import CheckoutRequest
from app.services.serialize import model_to_dict
from app.services.plans import normalize_plan

router = APIRouter(prefix="/billing", tags=["Billing"])

PLAN_PRICE_ENV = {
    "individual_elite": "stripe_price_individual_elite",
    "business_owner": "stripe_price_business_owner",
    "white_label_platform": "stripe_price_white_label_platform",
    # Backward compatibility for previous public plan IDs
    "individual_starter": "stripe_price_individual_elite",
    "individual_pro": "stripe_price_individual_elite",
    "business_growth": "stripe_price_business_owner",
    "business_scale": "stripe_price_business_owner",
    "business_enterprise": "stripe_price_business_owner",
    "white_label_agency": "stripe_price_white_label_platform",
    "white_label_studio": "stripe_price_white_label_platform",
    "white_label": "stripe_price_white_label_platform",
}

PLAN_LABELS = {
    "individual_elite": "Individual Elite",
    "business_owner": "Business Owner",
    "white_label_platform": "White Label Platform",
    # Backward-compatible labels
    "individual_starter": "Individual Elite",
    "individual_pro": "Individual Elite",
    "business_growth": "Business Owner",
    "business_scale": "Business Owner",
    "business_enterprise": "Business Owner",
    "white_label_agency": "White Label Platform",
    "white_label_studio": "White Label Platform",
    "white_label": "White Label Platform",
}

def _stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(500, "STRIPE_SECRET_KEY is missing")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe

def price_for_plan(plan: str) -> str:
    plan = normalize_plan(plan)
    key = PLAN_PRICE_ENV.get(plan)
    price_id = getattr(settings, key, None) if key else None
    if not price_id:
        raise HTTPException(400, f"Stripe price ID missing for plan: {plan}")
    return price_id

def create_checkout_session_for_user(db: Session, user: User, plan: str) -> dict:
    plan = normalize_plan(plan)
    if not settings.payment_required:
        sub = Subscription(tenant_id=user.tenant_id, user_id=user.id, plan=plan, status="trialing")
        user.is_active = True
        user.payment_status = "trialing"
        db.add(user); db.add(sub); db.commit()
        return {"checkout_url": None, "session_id": None, "plan": plan, "payment_required": False}
    stripe = _stripe()
    price_id = price_for_plan(plan)
    success_url = settings.frontend_base_url.rstrip("/") + settings.default_success_url + "&session_id={CHECKOUT_SESSION_ID}"
    cancel_url = settings.frontend_base_url.rstrip("/") + settings.default_cancel_url
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(email=user.email, name=user.full_name, metadata={"user_id": str(user.id), "tenant_id": str(user.tenant_id)})
        customer_id = customer["id"]
        user.stripe_customer_id = customer_id
        db.add(user); db.commit(); db.refresh(user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
        metadata={"user_id": str(user.id), "tenant_id": str(user.tenant_id), "plan": plan},
        subscription_data={"metadata": {"user_id": str(user.id), "tenant_id": str(user.tenant_id), "plan": plan}},
    )
    sub = Subscription(
        tenant_id=user.tenant_id,
        user_id=user.id,
        stripe_customer_id=customer_id,
        plan=plan,
        status="incomplete",
        checkout_session_id=session["id"],
        stripe_price_id=price_id,
    )
    db.add(sub); db.commit()
    return {"checkout_url": session["url"], "session_id": session["id"], "plan": plan}

@router.get("/plans")
def plans():
    """Public plan metadata used by the front page and signup flow."""
    return {
        "individual": [
            {
                "id": "individual_elite",
                "name": "Individual Elite",
                "price": "$99/mo",
                "best_for": "individuals, creators, students, founders, freelancers, researchers, and independent operators managing serious funding workflows",
                "features": [
                    "Unlimited grant discovery",
                    "AI proposal drafting and application narratives",
                    "Submission tracking and approval center",
                    "Funding health score and AI recommendations",
                    "Agent Pipeline for eligibility, budget, compliance, review, and submission planning",
                    "PDF exports, document uploads, and grant alerts",
                    "Personal funding profile and saved opportunity workspace",
                    "1 user seat",
                ],
                "limits": [
                    "No team workspace",
                    "No white-label portal",
                    "No API resale rights",
                ],
            }
        ],
        "business": [
            {
                "id": "business_owner",
                "name": "Business Owner",
                "price": "$299/mo",
                "best_for": "business owners, nonprofits, startups, consultants, and small teams that need a full funding operating system",
                "features": [
                    "Everything in Individual Elite",
                    "Business, nonprofit, public, private, corporate, and foundation grant intelligence",
                    "Organization Brain with shared business funding memory",
                    "Team workspace for up to 5 seats",
                    "Multi-application pipeline and approval center",
                    "Budget narrative support and submission package tracking",
                    "Priority alerts and business-focused opportunity radar",
                ],
                "limits": [
                    "No white-label client portal",
                    "No resale/custom-domain platform rights",
                ],
            }
        ],
        "white_label": [
            {
                "id": "white_label_platform",
                "name": "White Label Platform",
                "price": "$5,000+/yr",
                "best_for": "agencies, consultants, accelerators, and companies that want to sell Mogul Grant System as their own branded funding platform",
                "features": [
                    "Everything in Business Owner",
                    "Custom branding, colors, logo, and client portal",
                    "White-label tenant controls and admin dashboard",
                    "Client workspace management",
                    "Custom domain-ready architecture",
                    "Partner analytics and high-volume AI workflows",
                    "Dedicated onboarding and enterprise support",
                ],
                "limits": [],
            }
        ],
    }


@router.post("/create-checkout")
def create_checkout(payload: CheckoutRequest, db: Session = Depends(get_db), user = Depends(current_user)):
    if not settings.payment_required:
        return {"payment_required": False, "message": "Stripe is disabled. User already has access.", "checkout_url": None, "plan": payload.plan}
    return create_checkout_session_for_user(db, user, payload.plan)

@router.get("/status")
def billing_status(db: Session = Depends(get_db), user = Depends(current_user)):
    row = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.id.desc()).first()
    has_access = True if not settings.payment_required else bool(user.is_active and user.payment_status in {"active", "trialing"} and row and row.status in {"active", "trialing"})
    return {"payment_required": settings.payment_required, "user_payment_status": user.payment_status, "has_paid_access": has_access, "subscription": model_to_dict(row) if row else None}

def activate_user_subscription(db: Session, user_id: int, customer_id: str | None, subscription_id: str | None, plan: str | None, status: str, current_period_end: str | None = None, checkout_session_id: str | None = None):
    plan = normalize_plan(plan) if plan else plan
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    user.stripe_customer_id = customer_id or user.stripe_customer_id
    user.payment_status = status
    user.is_active = status in {"active", "trialing"}
    sub = None
    if checkout_session_id:
        sub = db.query(Subscription).filter(Subscription.checkout_session_id == checkout_session_id).first()
    if not sub and subscription_id:
        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription_id).first()
    if not sub:
        sub = Subscription(tenant_id=user.tenant_id, user_id=user.id)
    sub.stripe_customer_id = customer_id or sub.stripe_customer_id
    sub.stripe_subscription_id = subscription_id or sub.stripe_subscription_id
    sub.plan = plan or sub.plan
    sub.status = status
    sub.current_period_end = current_period_end or sub.current_period_end
    db.add(user); db.add(sub); db.commit()

@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if settings.stripe_webhook_secret and settings.stripe_secret_key:
        stripe = _stripe()
        try:
            event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
        except Exception as exc:
            raise HTTPException(400, "Invalid Stripe webhook") from exc
    else:
        event = await request.json()
    etype = event.get("type")
    obj = event.get("data", {}).get("object", {})
    if etype == "checkout.session.completed":
        meta = obj.get("metadata", {}) or {}
        user_id = int(meta.get("user_id"))
        activate_user_subscription(db, user_id, obj.get("customer"), obj.get("subscription"), meta.get("plan"), "active", checkout_session_id=obj.get("id"))
    elif etype in {"customer.subscription.updated", "customer.subscription.created", "customer.subscription.deleted"}:
        meta = obj.get("metadata", {}) or {}
        user_id = meta.get("user_id")
        status = obj.get("status", "inactive")
        if user_id:
            period_end = obj.get("current_period_end")
            period_end_str = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat() if period_end else None
            activate_user_subscription(db, int(user_id), obj.get("customer"), obj.get("id"), meta.get("plan"), status, period_end_str)
    return {"received": True, "type": etype}
