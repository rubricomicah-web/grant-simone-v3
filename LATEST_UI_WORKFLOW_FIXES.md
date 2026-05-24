# Latest UI + Workflow Fixes

This build focuses on the current issues found in the live Render app.

## Fixed

- Agent Pipeline no longer exposes internal fields such as IDs, boolean flags, memory counters, or `[object Object]`.
- Agent activity is now written in human/client language.
- Workflow summary shows recommended grant, readiness, approval requirement, and next action.
- Recommended next actions now appear after workflow runs.
- Notification Refresh now reloads settings and alerts.
- Mark Read now refreshes notifications and shows a next recommended action instead of leaving the user stuck.
- Admin Plan Matrix has a local fallback if the API fails, so the admin can still view plan tiers.
- Plan cards are cleaner and easier to understand.
- White Label page now explains access requirements for white-label tenants and handles permission errors more clearly.
- Updated CSS for clean agent cards, plan cards, and action cards.

## Next Database Work

Recommended database upgrades:
- Add persistent task/action table.
- Add tenant invites.
- Add user-to-tenant role management.
- Add custom domain mapping.
- Add notification next_action fields.
- Add white-label client accounts.
