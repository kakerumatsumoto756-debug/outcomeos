# OutcomeOS — Submission materials (English)

> These are application-ready descriptions, not evidence that you have submitted the forms. Add your actual GitHub and live URL, own team identity, and real test results. Do not invent users, revenue, model accuracy, or traction.

## Product name

OutcomeOS — Decision Intelligence Powered by Prediction Markets

## One-line pitch

OutcomeOS is a decision memory layer that connects teams' forecasts and evidence with live Panta prediction-market signals, then measures what happened and how well the team predicted it.

## Short description (copy to project page)

Teams make high-stakes decisions using fragmented opinions and scattered information, but rarely document what they expected, what the market believed, and what actually happened. OutcomeOS turns each decision into a measurable YES/NO outcome with a deadline, evidence, participant forecasts, and linked Panta market quotes. It then preserves quote history, flags forecast-versus-market divergence, and scores accuracy after resolution. We use Panta as a read-only source of external market intelligence—not as a betting destination—so users can improve decisions without trading or holding funds.

## Problem and solution (application response)

**Problem.** Decision-making is often unstructured. Teams forget who predicted what, why, and when. Individual estimates, external market signals, and final outcomes remain disconnected, making it difficult to learn and improve.

**Solution.** OutcomeOS stores each decision, its resolution criteria, time-stamped team forecasts, relevant evidence and linked Panta contracts. A team can compare its estimates with the market's observed YES/NO price, monitor price changes and resolve the question to calculate Brier accuracy scores. A controlled, expiring public report can show aggregated insight while hiding member identities and private notes.

## Exact Panta integration

OutcomeOS uses the official Panta REST API with a server-side `X-Api-Key` credential:

1. `GET /categories/` discovers the market-category allowlist.
2. `GET /markets/` finds markets with category/phase filters and pagination.
3. `GET /markets/{marketId}/` retrieves individual contracts and available YES/NO quotes.
4. A linked market records validated quote snapshots with source attribution and timestamp, ignoring invalid or unchanged values.
5. A team can compare the latest Panta YES quote against its members' most recent estimates, observe meaningful divergence and share anonymized reports.

**Important:** Market prices can include spreads/fees and are not asserted to be calibrated event probabilities. The app does not create markets, execute trades, custody assets, sign wallets or claim winnings. Only real responses from Panta are labeled "Live Panta"; synthetic local examples are explicitly labeled demo. This read-only implementation is a meaningful and safe application of Panta's market-data capabilities.

## Product originality

OutcomeOS makes prediction-market data a component of an auditable business-decision workflow. Instead of optimizing for trades, it measures whether a team's forecasts were useful, aligns external market contracts to actual decision rules, and closes the loop with retrospective scoring and evidence. The novelty is the full decision memory and calibration workflow, rather than merely listing market prices.

## Technical implementation

- Frontend: vanilla JavaScript, semantic HTML/CSS, responsive app + public landing page.
- Backend: Python 3 HTTP service with session authentication, CSRF tokens and permission-scoped workspaces.
- Database: SQLite locally; PostgreSQL (Neon) on public Render hosting.
- Panta: server-side, read-only API adapter; schema/quote validation; bounded requests and descriptive errors.
- Key workflows: decisions, forecasts, evidence, market links, quote snapshots, alerts, scores, exports, audit trail, public reports with revocable 7-day links.
- Deployment: Docker, free Render Blueprint, TLS session cookies, durable external Neon database.
- Validation: automated unit/HTTP tests and browser walkthrough, if locally verified. Live Panta/Neon deployment checks must be filled in with actual results.

## Target customers and business model

Initial target: founders, product teams, research teams and investment/strategy analysts making measurable forecasts for product launches, hiring, growth, regulation or other uncertain outcomes. Potential go-to-market: invite-led pilot with 5–10 teams and a weekly "decision review" ritual; publish case studies with explicit consent. Potential monetization: team subscriptions for persistent workspaces, advanced analytics, role controls, integrations and reporting. No existing customers, paying users or subscription feature is claimed.

## Traction / honest validation statement

"Built a functional integrated product with market discovery, forecasts, recorded historical signals and shareable decision reports. We have not yet measured retained users, paid subscriptions or externally validated forecast uplift. We intend to run founder and analyst pilots next." Adjust the first clause if production tests are incomplete at submission time.

## Requested submission fields — fill with real values

- **Live application:** `[PASTE REAL RENDER HTTPS URL]`
- **Source repository:** `[PASTE YOUR REAL GITHUB URL]`
- **Presentation video:** `[PASTE LINK TO ACTUAL 2-3 MIN VIDEO]`
- **Product demo video:** `[PASTE LINK TO ACTUAL VIDEO <=3 MIN]`
- **Founder/team details:** `[FILL WITH YOUR OWN INFORMATION]`
- **Panta live market tested:** `[ACTUAL MARKET ID + DATE/TIME OR MARK NOT TESTED]`
- **Blockchain / tools:** Panta API; read-only market signals sourced from prediction markets in Panta's ecosystem. Do not claim this app deploys its own on-chain program.

## Final submission checklist

- [ ] Register for Colosseum Crypto World's Fair before deadline.
- [ ] Make GitHub accessible to judges; remove secrets and sample credentials.
- [ ] Deploy public HTTPS app on Render connected to Neon PostgreSQL; test real sign-up.
- [ ] Revoke old exposed Panta credential and use new live key in Render secret manager.
- [ ] Verify actual Panta results in the hosted app and choose a truly relevant contract.
- [ ] Record real two-to-three-minute founder presentation and <=3-minute product demonstration; test audio and link permissions.
- [ ] Use only your actual results and screenshots. No misleading claims about public traffic, revenue or accuracy.
- [ ] Submit to **Colosseum official portal** by **October 12, 2026**.
- [ ] **Separately** submit to **Superteam Earn → Panta API Sidetrack**, in English.
- [ ] Open both entries after submission and confirm successful status.

Official requirements: https://colosseum.com/hackathon?year=fall2026 and https://superteam.fun/earn/listing/panta-api-side-track
