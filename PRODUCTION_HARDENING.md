# Mogul Grant System production hardening added

This package includes:

- Email verification endpoints and Resend integration
- Password reset request and reset endpoints
- Login attempt logging and temporary account lockout
- Refresh token endpoint
- Usage tracking endpoint and plan-limit compatibility
- Admin user management endpoints
- Security headers middleware
- Optional Sentry crash monitoring
- Lightweight DB migrations for older Railway databases
- Document parsing foundation for TXT/CSV uploads
- Grant deduplication canonical index foundation
- Deadline urgency helper foundation
- PWA manifest/service-worker foundation
- Backup metadata helper and Railway backup guidance

## Recommended Railway vars

```env
PAYMENTS_ENABLED=false
EMAIL_NOTIFICATIONS_ENABLED=false
EMAIL_VERIFICATION_REQUIRED=false
PASSWORD_RESET_ENABLED=true
SECURITY_HEADERS_ENABLED=true
SENTRY_DSN=
MAX_LOGIN_ATTEMPTS=8
LOCKOUT_MINUTES=15
```

Set EMAIL_VERIFICATION_REQUIRED=true only after your Resend sender/domain is verified.
