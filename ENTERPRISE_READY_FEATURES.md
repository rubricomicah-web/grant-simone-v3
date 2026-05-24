# Mogul Grant System Enterprise-Ready Upgrade

This build keeps Stripe disabled, but includes the code foundation for every major missing production feature.

## Included now

### 1. Autonomous Browser Agent Foundation
- Endpoint: `POST /api/automation/browser/prepare`
- Creates browser automation tasks.
- Never submits without human approval.
- Safe default: prepares checklist/application packet only.
- To enable real browser checks later:
  - add `playwright` to requirements
  - run `playwright install chromium`
  - set `BROWSER_AUTOMATION_ENABLED=true`

### 2. Vector Memory / Semantic Recall Foundation
- Service: `app/services/embeddings.py`
- Uses deterministic local embeddings now, no paid API required.
- Can later be upgraded to OpenAI/Groq embeddings + pgvector.

### 3. Real-Time Funding Monitoring Foundation
- Worker: `python -m app.workers.worker`
- Endpoint: `POST /api/monitoring/run-now`
- Scans profiles and creates notifications for new matching verified grants.
- Enable scheduled scan with `FUNDING_MONITOR_ENABLED=true`.

### 4. Advanced Hybrid Search
- Endpoint: `GET /api/search/grants?q=...`
- Combines keyword search + semantic matching + verified-source boost.

### 5. Application Outcome Intelligence
- Endpoint: `POST /api/outcomes`
- Tracks awarded/rejected/under_review outcomes.
- Endpoint: `GET /api/outcomes/summary`
- Supports future success-rate analytics.

### 6. White-Label Tenant Domain Foundation
- New `tenant_domains` table for custom domain/subdomain verification.
- Existing RBAC protects admin/white-label access.

### 7. Storage Adapter
- Default: local Railway storage.
- Future: Cloudflare R2/S3 with `STORAGE_BACKEND=s3`.
- No route changes needed later.

### 8. Worker Procfile
- Web service: FastAPI.
- Worker service: funding monitor / background jobs.

## Safe defaults

```env
PAYMENTS_ENABLED=false
EMAIL_NOTIFICATIONS_ENABLED=false
BROWSER_AUTOMATION_ENABLED=false
FUNDING_MONITOR_ENABLED=false
STORAGE_BACKEND=local
```

## Optional later env vars

```env
# Browser automation
BROWSER_AUTOMATION_ENABLED=true

# Background funding monitor
FUNDING_MONITOR_ENABLED=true
WORKER_INTERVAL_SECONDS=21600

# Cloudflare R2 / S3
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET=

# Resend email
EMAIL_NOTIFICATIONS_ENABLED=true
RESEND_API_KEY=
RESEND_FROM_EMAIL="Mogul Grant System <notifications@yourdomain.com>"
```

## Important legal/safety behavior
Mogul Grant System can prepare and organize applications, but should not submit grant applications without explicit user approval because many portals require certifications, signatures, and legally binding attestations.
