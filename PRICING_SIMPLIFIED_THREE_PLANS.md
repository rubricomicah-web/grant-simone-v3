# Mogul Grant System Pricing Simplification

This build removes the older multi-tier individual pricing and simplifies the public offer into three paid plan categories:

## 1. Individual Elite — $99/mo
For individuals, students, creators, researchers, freelancers, founders, and independent operators.

Includes:
- Grant discovery
- AI proposal drafting
- Funding health score
- Agent Pipeline
- Submission tracking
- PDF exports and alerts
- 1 user seat

## 2. Business Owner — $299/mo
For business owners, nonprofits, startups, consultants, and small teams.

Includes:
- Everything in Individual Elite
- Organization Brain
- Team workspace up to 5 seats
- Business/nonprofit/private/foundation grant intelligence
- Multi-application approval center
- Budget narrative and submission package support

## 3. White Label Platform — $5,000+/yr
For agencies, consultants, accelerators, and companies that want to sell Mogul Grant System as their own branded funding platform.

Includes:
- Everything in Business Owner
- White-label tenant controls
- Custom branding
- Client portal
- Custom-domain-ready architecture
- Partner analytics
- Enterprise support

## Backward Compatibility
The following old IDs are automatically normalized:

- `individual_starter` → `individual_elite`
- `individual_pro` → `individual_elite`
- `business_growth`, `business_scale`, `business_enterprise` → `business_owner`
- `white_label_agency`, `white_label_studio`, `white_label` → `white_label_platform`

## Stripe Environment Variables
Use these going forward:

```env
STRIPE_PRICE_INDIVIDUAL_ELITE=
STRIPE_PRICE_BUSINESS_OWNER=
STRIPE_PRICE_WHITE_LABEL_PLATFORM=
```
