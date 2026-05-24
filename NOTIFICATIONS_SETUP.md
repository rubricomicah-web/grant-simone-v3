# Mogul Grant System Notifications Setup with Resend

This version supports both in-platform notifications and real email alerts through **Resend**.

## What it does

- Shows notification badge inside the platform
- Lets users manually scan for matching grants
- Railway worker scans paid users every 15 minutes
- Sends email alerts through Resend when configured
- Lets users set minimum match score for alerts

## Resend setup

1. Create or log in to your Resend account.
2. Add and verify your sending domain.
3. Create an API key.
4. Add the API key and sender email in Railway.

## Railway environment variables

```env
RESEND_API_KEY=re_your_resend_api_key
RESEND_FROM_EMAIL="Mogul Grant System <notifications@yourdomain.com>"
EMAIL_NOTIFICATIONS_ENABLED=true
```

Use a verified domain email in `RESEND_FROM_EMAIL`. Example:

```env
RESEND_FROM_EMAIL="Mogul Grant System <alerts@grantsimone.ai>"
```

## Railway worker

The existing `Procfile` already has:

```text
worker: python -m app.workers.worker
```

Create a second Railway service using the same repo and set the start command to:

```text
python -m app.workers.worker
```

The worker checks queued AI workflows and periodically creates grant-match notifications.

## How users receive alerts

When a paid user has a profile and Mogul Grant System finds a verified funding match above their chosen score:

1. A platform notification is created.
2. The notification badge increases.
3. If email alerts are enabled, Resend sends a branded email.
