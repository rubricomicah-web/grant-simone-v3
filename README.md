# Mogul Grant System - People + Organizations Edition

Railway-ready FastAPI + Groq grant platform with a plain HTML/CSS/JS frontend. No Next.js. No Docker.

## What changed

This version supports monthly subscribers who are:

- normal individuals looking for personal assistance, scholarships, education funding, housing help, workforce training, hardship resources, veteran support, family support, homeowner/renter resources
- business owners
- startups
- nonprofits
- grant consultants and agencies
- white-label companies

## Core features

- Login/signup with account type
- Funding Profiles for individuals and organizations
- Verified funding discovery with audience/category filtering
- Individual-oriented funding sources: Benefits.gov, StudentAid.gov, CareerOneStop, USA.gov, SBA
- Organization-oriented sources: Grants.gov, SBA, USDA pathways
- Groq-powered application narrative/proposal generation
- Application tracker with approval gate
- AI workflow orchestrator
- White-label tenant settings
- Stripe-ready billing routes
- Railway-ready Procfile and Nixpacks config

## Railway setup

1. Upload this repo to GitHub.
2. Create a Railway project.
3. Add PostgreSQL.
4. Set environment variables from `.env.example`.
5. Deploy.

## Important environment variables

```env
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=change-this
GROQ_API_KEY=your-groq-key
GROQ_MODEL=llama-3.3-70b-versatile
PAYMENT_REQUIRED=false
STRIPE_SECRET_KEY=optional later
STRIPE_WEBHOOK_SECRET=optional later
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

## Legal / compliance note

Mogul Grant System can prepare applications and guide users, but the platform keeps an approval gate before submission. Many grants and assistance programs require user certifications, signatures, or portal-specific terms.
