# MCP Concepts Integrated into Mogul Grant System

This build integrates the useful ideas from the MCP grant hunter codebase without turning Mogul into a grants.gov-only clone.

## Added/Improved

- Async funding fetch architecture
- Retry/backoff request handling
- Funding opportunity normalization layer
- Business-aware opportunity matching
- Cleaner funding recommendation logic
- Organization profile intelligence
- Proposal generation stabilization
- Safer button/action handling
- Improved application routing foundations
- Structured logging foundations
- Multi-source funding preparation architecture

## New files

- `app/services/funding_engine.py`
- `app/services/profile_intelligence.py`
- `app/services/proposal_stabilizer.py`
- `app/services/structured_logging.py`

## Important product decision

Mogul Grant System should show verified opportunities only. It should not pad searches with fake/dummy grants. The multi-source engine is prepared for SBA, SBIR, state/local, private foundation, corporate, accelerator, and other verified adapters once real sources or approved feeds are connected.
