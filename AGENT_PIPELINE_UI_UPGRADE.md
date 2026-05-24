# Agent Pipeline UI Upgrade

The Agent Pipeline page has been changed from a raw debug-style log into a clean AI Operations Center.

## Updated experience

- Visual pipeline stepper
- Executive pipeline summary card
- Compact live agent activity cards
- Artifacts section for proposal/application/deadline outputs
- No `[object Object]` rendering
- Duplicate agent output is reduced by updating one agent state per workflow

## Agents shown

- Grant Hunter
- Eligibility
- Memory
- Budget
- Compliance
- Proposal Writer
- Reviewer
- Submission Planner
- Deadline Monitor
- Notification

## Backend change

`log_agent()` now updates the existing agent state for a workflow + agent name instead of endlessly appending duplicates.
