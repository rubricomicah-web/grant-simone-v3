# Mogul Grant System Feature Gating + Client Profile Fix

This build fixes two selling-critical issues:

1. Features are now restricted by subscription plan in the frontend and backend.
2. Users now have a Client Profile page to view account, workspace, plan, usage, included features, and funding profiles.

## Backend enforcement

The backend now blocks unauthorized API access, not only hidden UI items.

Examples:
- Starter users cannot run AI workflows.
- Starter users cannot access private/corporate grant intelligence.
- Admin controls require Enterprise or White Label access.
- White Label controls require a White Label plan.
- Document/proposal/workflow limits are enforced by plan.

## Frontend enforcement

The sidebar hides unavailable features based on `/api/auth/me` feature flags.
If a user somehow tries to open a locked page, the app shows an upgrade notice.

## Client Profile

New API:

```text
GET /api/auth/client-profile
```

Shows:
- user information
- workspace information
- selected plan
- subscription status
- usage counts
- included/locked feature access
- saved funding profiles

## Logout fix

Logout now clears local storage and redirects to:

```text
/signup.html?mode=login
```

This avoids the previous `/dashboard` JSON 404 issue.
