# Curated Verified Grants Layer

This build adds a real curated national funding layer from the team-provided May 2026 list. These are not dummy grants. They are official/private/corporate source records that stay marked as `National`, so they can appear for every U.S. state when the user need matches.

Included sources:

- Amber Grant / WomensNet
- IFundWomen
- Hello Alice
- FedEx Small Business Grant Contest
- Visa Everywhere Initiative
- MBDA Business Grants & Programs
- Verizon Small Business Digital Ready
- Cartier Women's Initiative
- NASE Growth Grants

Search behavior:

- National grants can appear for any selected U.S. state.
- State-specific grants only appear for matching states.
- No dummy/fake fallback grants are generated.
- If no verified relevant match exists, the API returns an honest no-results message.
- Business type and needs are matched using title, description, eligibility, and curated metadata tags.

Important: users should still verify eligibility and deadlines on official source pages before applying.
