# Superteam Earn — Panta API Sidetrack submission (English)

## Project title
**OutcomeOS — Decision Intelligence Powered by Prediction Markets**

## Short hook
**Turn market signals into measurable team decisions.**

## Full submission description

OutcomeOS is a collaborative decision-learning workspace that makes prediction-market intelligence useful beyond trading. Teams frequently make forecasts about launches, products, research questions, and uncertain external events, but rarely record probabilities, evidence, market context, and final outcomes together. OutcomeOS gives them one place to do that.

Users create a clearly defined YES/NO question with a deadline and resolution criteria; add individual probability estimates and evidence; discover Panta markets; and link an appropriate prediction-market contract when the underlying outcome truly matches. OutcomeOS can store time-stamped YES/NO quote snapshots from Panta, flag differences between market prices and team forecasts, and score the accuracy of forecasts after resolution. Owners can generate expiring, revocable read-only reports that omit private notes and personal identities.

Our differentiation is a **decision memory and learning loop**: define a question -> gather internal forecasts -> connect an outside market signal -> monitor changes -> resolve the event -> score what happened. We are not another exchange, wallet, or betting interface. The Panta API is the market-data layer that enables the external signal. Trading, transaction signing, wallet custody, and financial advice are intentionally outside this version.

## Why Panta matters

1. The Panta API supplies discoverable, real markets and structured metadata.
2. Its market-detail endpoints provide available quoted YES/NO prices, which are used as **market observations**, not guaranteed real-world probabilities.
3. OutcomeOS uses a server-side authenticated API adapter and saves attributed market snapshots for auditability.
4. Users compare their own forecasts with changes in the Panta market and later learn from outcome scoring.
5. Read-only design allows teams to use prediction-market intelligence without first needing to trade.

## Implemented technical scope

- Multi-user workspaces with basic access control, invites, decisions, and individual probability estimates.
- Dated evidence and activity views.
- Panta market discovery, details, quote validation, and snapshot storage through a read-only server API integration.
- Quote change and divergence analysis; calibrated-feedback workflow with Brier scores after actual or explicitly labeled test resolution.
- Expiring, revocable, privacy-filtered report links and export features.
- Python web backend, JavaScript frontend, SQLite local storage, optional PostgreSQL cloud storage, Docker and Render deployment configuration.

## Product status — accurate disclosure

This is a functional beta with **33 passing local automated tests** in the latest packaged verification report. The earlier local screenshot displayed 30 markets in Live Panta mode. A newly rotated Panta key, final public Render deployment, and Neon persistence still require hands-on acceptance testing before public claims are finalized. No active customers, paid users, audited security, or proven prediction uplift are claimed.

## Intended users and potential impact

The initial audience is founders, product teams, research groups, and analysts who revisit uncertain decisions every week. A longer-term subscription business could support persistent team workspaces, advanced history, privacy controls, integrations, and audit-ready reports. These plans are hypotheses, not current paid features.

## Links to insert before submission

- **Live product:** [YOUR VERIFIED HTTPS URL]
- **Repository:** [YOUR GITHUB PROJECT URL]
- **Pitch video:** [YOUR ACTUAL VIDEO URL]
- **Product demo:** [YOUR ACTUAL VIDEO URL]
- **Colosseum submission:** [YOUR CONFIRMED COLOSSEUM PROJECT LINK]
- **Contact:** [YOUR VERIFIED CONTACT]

## Notes for the reviewer

Panta integration is via market discovery and data, not market creation or execution. In the demo, synthetic entries, test resolutions, and real Panta market records are labeled separately. A new key must replace the earlier exposed credential.

## Official submission route

Submit OutcomeOS to **both** Colosseum and Superteam Earn. English submission and a working demonstration are required. The official sidetrack listing is https://superteam.fun/earn/listing/panta-api-side-track
