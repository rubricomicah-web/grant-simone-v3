# Payment Mode Setup

This version is configured for **no Stripe required yet**.

Users can choose a plan on the front page, sign up, and immediately use the platform. The selected plan is still saved to the account subscription record, so you can turn on Stripe later without rebuilding the app.

## Current Railway setting

```env
PAYMENT_REQUIRED=false
```

## When you get a Stripe account later

1. Create your Stripe products/prices.
2. Add these env vars in Railway:

```env
PAYMENT_REQUIRED=true
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_INDIVIDUAL_STARTER=price_...
STRIPE_PRICE_INDIVIDUAL_PRO=price_...
STRIPE_PRICE_INDIVIDUAL_ELITE=price_...
STRIPE_PRICE_BUSINESS_GROWTH=price_...
STRIPE_PRICE_BUSINESS_SCALE=price_...
STRIPE_PRICE_BUSINESS_ENTERPRISE=price_...
STRIPE_PRICE_WHITE_LABEL_AGENCY=price_...
STRIPE_PRICE_WHITE_LABEL_STUDIO=price_...
STRIPE_PRICE_WHITE_LABEL_PLATFORM=price_...
```

3. Add webhook URL in Stripe:

```text
https://your-railway-domain.up.railway.app/api/billing/stripe-webhook
```

4. Redeploy Railway.

Signup flow will automatically become:

```text
Choose plan -> Signup -> Instant active account now. Later: Choose plan -> Signup -> Stripe Checkout -> Active account
```

For now, it is:

```text
Choose plan -> Signup -> Active account
```
