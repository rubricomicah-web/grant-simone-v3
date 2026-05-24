# Mogul Grant System AI Agents

This version includes a working approval-gated agent pipeline.

## Agents in the full funding pipeline

1. Grant Hunter Agent
   - Selects the user-selected grant, or automatically finds the best verified grant if no Grant ID is provided.
2. Eligibility Agent
   - Scores likely fit based on profile, grant text, source confidence, and memory.
3. Memory Agent
   - Pulls saved organization/profile memories for better proposal context.
4. Budget Agent
   - Creates a draft use-of-funds plan.
5. Compliance Agent
   - Builds required-item checklist and flags missing profile details.
6. Proposal Writer Agent
   - Generates the proposal/application narrative and PDF.
7. Reviewer Agent
   - Scores the proposal and returns improvement guidance.
8. Submission Planner Agent
   - Creates an application package with client approval required.
9. Deadline Monitor Agent
   - Adds deadline/next-action tracking.
10. Notification Agent
   - Creates an in-platform alert when the package is ready.

## How to use

Dashboard > AI Workflows > select funding profile > Run Full Funding Pipeline.

Grant ID is optional. If it is blank, Mogul Grant System will automatically select the best verified funding match first.

## Safety

The system does not auto-submit applications. It prepares the package and sets status to `ready_for_client_approval`.
