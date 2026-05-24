# Mogul Grant System Credit + Plan Preview System

## Monthly Credits
Credits are now enforced on the backend, not only the UI.

Default monthly credits:

- Individual Starter: 50 credits/month
- Individual Pro: 300 credits/month
- Individual Elite: 1,000 credits/month
- Business Growth: 2,000 credits/month
- Business Scale: 7,500 credits/month
- Business Enterprise: 25,000 credits/month
- White Label Agency: 5,000 credits/month
- White Label Studio: 20,000 credits/month
- White Label Platform: unlimited-style high limits

## Credit Costs

- Grant search: 1 credit
- Proposal generation: 5 credits
- AI workflow run: 10 credits
- Document upload: 2 credits
- PDF export/download: 1 credit

If the user does not have enough credits, the backend returns HTTP 403 with an upgrade/add-credit message.

## Admin Plan Matrix
Admins with eligible plans can now load all plan tiers and see:

- Monthly price
- Credits/month
- Grant searches
- AI proposals
- AI workflows
- PDF exports
- Documents
- Team members
- Private grants access
- White-label access
- Admin access

## Admin Preview
Admin has a `View as this plan` action through the Admin Plan Matrix. It shows what features are enabled for that tier without changing the admin account.

## Admin Credit Adjustment
Backend endpoint:

```http
POST /admin/users/{user_id}/credits
```

Body:

```json
{
  "credits": 100,
  "reason": "manual top-up"
}
```

This adds monthly credit adjustment for the selected user.
