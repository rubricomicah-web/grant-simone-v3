# Funding Health Score

Mogul Grant System now computes a non-random, explainable Funding Health Score from real account data.

## Formula

- Eligibility Match: 25%
- Organization Readiness: 20%
- Proposal Strength: 20%
- Financial Stability: 15%
- Compliance Readiness: 10%
- Historical Performance: 5%
- Submission Timing: 5%

## What it uses

- Funding profile completeness
- State/location and funding goal data
- Budget/income context
- Uploaded documents
- Proposal score
- Completed agent workflows
- Application status
- Funding outcomes
- Deadline timing

## UI

The dashboard now shows:

- Score out of 100
- Readiness label
- Component scores
- Strengths
- Risks
- Recommended actions

The API endpoint is:

```text
GET /api/analytics/funding-health
```

Optional:

```text
GET /api/analytics/funding-health?organization_id=1
```
