
# Mogul Grant System Production Upgrade — No Stripe

This build keeps Stripe disabled but adds the missing production foundations:

- Live Grants.gov ingestion endpoint: `POST /api/grants/ingest-live`
- Strict verified funding results only; no verified-source or dummy grants
- Role-based admin protection
- White-label access limited to white-label plans and owner/admin users
- Plan limit enforcement for searches, proposals, workflows, and documents
- Document vault upload/download
- Proposal editing and version history
- Approval-gated application tracker
- Legal disclaimer in dashboard
- Clean public footer

Keep Railway variables as booleans without quotes:

```env
PAYMENTS_ENABLED=false
PAYMENT_REQUIRED=false
EMAIL_NOTIFICATIONS_ENABLED=false
```

Stripe can be added later by setting `PAYMENT_REQUIRED=true` and adding Stripe keys.
