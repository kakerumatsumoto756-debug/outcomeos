# OutcomeOS — submission briefing (English)

**One-liner:** OutcomeOS is the decision memory layer for the uncertain world, combining human forecasts, evidence, and prediction market prices to make decisions measurable and accountable.

**Problem:** Teams make consequential decisions based on scattered forecasts and anecdotal confidence. After the deadline they often cannot reconstruct what was believed, what evidence was available, how opinions changed, or whether anyone's predictions were reliable.

**Solution:** Every decision lives in a persistent room with an objectively resolvable YES/NO question, expected downside, forecasts from individuals, evidence, relevant Panta contracts and successive quote snapshots. The room remains auditable after the outcome resolves. Calibration reveals whether confidence was warranted.

**What makes this different:** OutcomeOS uses prediction markets as a *decision-support substrate*, not a betting/trading destination. Individuals do not need to place positions. Teams can use live market prices as external informational signals while documenting why a particular market is (or isn't) equivalent to their own decision.

**Panta API:** Read-only `GET /markets/` discovery (official `/categories/` allowlist, phase filters, pagination), `GET /markets/{marketId}/` quote detail and saved price history via opt-in polling. Server-only key in `X-Api-Key` header. Relevant links are explicitly mapped to decisions with explanatory matching notes. Unavailable API returns an error; synthetic data is clearly marked DEMO. Implemented based on official docs—tested with a local loopback HTTP fixture but not yet validated against the actual Panta service without user credentials.

**Intended users:** Startup founders, product teams, organizational strategy teams, research collectives, analysts, and innovation units. Monetization possibility: hosted team SaaS with per-seat plans and retained decision/evidence records. **No paying customers or traction are claimed.**

## 2-minute pitch structure

1. **0:00–0:15 — Hook:** Why do important decisions get made without a record of what we thought would happen?
2. **0:15–0:35 — Problem:** Businesses forget their own forecasts and lack a standard way to compare them to actual outcomes.
3. **0:35–1:00 — Product:** Show a decision room, forecasts from teammates, a documented resolution criterion, and supporting evidence.
4. **1:00–1:25 — Panta integration:** Switch to Live Panta (if you have a working API key). Fetch market list, load market detail, link a matching real market and record a quote. Clearly identify live data and its timestamp.
5. **1:25–1:45 — Learning:** Resolve a decision, show team calibration and Brier score; explain how observed market prices are informative but not assumed calibrated probabilities.
6. **1:45–2:00 — Vision:** We want the shared operating system for disciplined, evidence-backed decisions.

## Non-negotiable validation checklist before submission

- [ ] Colosseum official eligibility and registration confirmed by applicant
- [ ] Official Colosseum submission completed
- [ ] Superteam Panta Sidetrack submission completed in English
- [ ] API key acquired and actual successful Panta live responses captured (currently unverified)
- [ ] A real market with matching outcome and settlement found and connected, or demo honestly scoped
- [ ] Real presentation + product demonstration video recorded
- [ ] Repo published or accessible to judges, and secrets checked
- [ ] Dates, current market-creation API scope, pricing and legal applicability verified
- [ ] Any use of pre-existing project code disclosed as required by hackathon rules

Official listing: https://superteam.fun/earn/listing/panta-api-side-track

Do not claim that filling out this template satisfies submission requirements.

## OutcomeOS v1.2 judge-access plan

**Do not put an API key in the project source, demo slides, or public submission form. Revoke any key disclosed in chat before deployment.**

Recommended demonstration sequence:

1. Show the product at a real HTTPS domain (if deployed) or capture a screen recording that clearly displays the working product.
2. Create a new decision with objective YES/NO settlement rules and a deadline.
3. Open **Market intelligence → Live Panta → Fetch live markets** and click **View quotes**. Record Panta source and last snapshot timestamps.
4. Link a Panta market to the decision **only if the event definition and resolution conditions match**, explain why the match is meaningful, and add a personal forecast.
5. Refresh live quote(s) for stored historical observations, show source/price change and team-vs-market signal divergence.
6. Generate a **Share decision report** link, open in an incognito window, and prove the judge can see the anonymized forecast/market report without an account.
7. Show the audit trail and how outcome resolution yields a Brier score. Explain that the current app does **not** place trades and market prices are not calibrated predictions.
8. Explicitly show that demo market cards are synthetic and not part of Panta.

For a clean public demo, set `OUTCOMEOS_SEED_EXAMPLES=0` so no fake starter forecasts appear. The HTTPS preview setup is in `docs/PUBLIC_PREVIEW.md`.

The repo includes unit/API tests, access control and public-share tests, and JavaScript syntax checks. Tests do not guarantee the live Panta API endpoints are reachable under a particular key. Tests also do not establish a security audit or live end-to-end deployment success.
