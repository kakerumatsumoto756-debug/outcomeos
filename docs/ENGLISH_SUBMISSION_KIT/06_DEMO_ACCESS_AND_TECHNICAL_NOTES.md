# Technical integration, architecture, judge access and validation (English)

## 1. Plain-language architecture

`Browser -> OutcomeOS Python backend -> Panta REST API (read-only)`

`Browser -> OutcomeOS Python backend -> PostgreSQL on Neon (hosted) / SQLite (local)`

The Panta secret is held only on the server. No key belongs in JavaScript, GitHub, the pitch deck, or a recorded demo. Authentication is accomplished by the documented `X-Api-Key` header. The Panta API is Solana-native, but OutcomeOS does not issue transactions or connect wallets.

## 2. Panta features used

- Market-category discovery and catalog browsing.
- Market-detail requests and available YES/NO quoted prices.
- Quote validation, attributed time-stamped snapshots, unchanged-quote deduplication.
- Mapping between a real contract and a compatible internal decision question.

**Deliberate exclusions:** market creation, buying/selling positions, order execution, claims, transaction signing, financial or betting advice. No artificial-intelligence prediction model is asserted.

## 3. Public access instructions for judges

- **Website:** [VERIFIED HTTPS URL]
- **Landing page:** open the website root.
- **Application:** click **Open app** or visit `[VERIFIED HTTPS URL]/app`.
- **Create a workspace:** judges may register with a unique email on the deployed application if this has been tested.
- **Market discovery:** **Market intelligence -> Live Panta -> Fetch live markets -> View quotes**.
- **Sample decision:** [EITHER provide safe tested demo account, or instruct judge to create own; never publish your personal login].
- **Sample share report:** [VERIFIED PUBLIC EXPIRING LINK, CREATED ONLY AFTER DEPLOYMENT].

Never advertise a test login until it has been provisioned and confirmed safe for public use. Render Free may take a minute to wake after inactivity.

## 4. Actual test evidence currently available

Local version 1.3 verification, dated October 9, 2026:

- Python unit and backend API tests: 33/33 passed.
- JavaScript syntax checks: passed.
- Local HTTP landing, app, health, registration, workspace and decision create/read: passed.
- Panta API interface tested with mocked responses; earlier local live catalog was shown in a user screenshot.

**Not yet verified for hosted version:** actual Render deployment, Neon remote read/write durability, fully rotated new Panta live credential, public browser walk-through and production security audit.

## 5. Security and privacy posture

Application includes PBKDF2 password hashes, server session cookies, CSRF checks, permission-scoped workspaces, and expiry/revocation of share links. A full independent security assessment, abuse protection review, and uptime validation have not been completed. Do not store sensitive enterprise forecasts in public beta before reviewing those risks.

## 6. Repository evidence

- Main entry: `main.py`
- Panta adapter: `app/panta.py`
- API routes: `app/http_api.py`
- Storage: `app/storage.py`, `app/postgres.py`
- User interface: `web/`
- Cloud deploy: `render.yaml`, `Dockerfile`, `requirements-cloud.txt`
- Verification: `tests/`, `docs/TEST_REPORT.md`, `docs/KNOWN_LIMITATIONS.md`

## 7. Read-only API usage example (architecture pseudocode)

```text
User -> OutcomeOS backend: Browse markets
OutcomeOS backend -> Panta API: GET /markets/ (X-Api-Key held server-side)
Panta -> OutcomeOS: Market catalog
User -> OutcomeOS backend: Open market
OutcomeOS backend -> Panta API: GET /markets/{marketId}/
OutcomeOS -> Database: Save timestamped valid quote snapshot
OutcomeOS -> User: Show quote, source, and comparison with forecasts
```

## 8. Sources

- Panta documentation: https://docs.panta.market/
- Official Panta Sidetrack listing: https://superteam.fun/earn/listing/panta-api-side-track
- Colosseum: https://colosseum.com/worldsfair
- Internal implementation limitations: `docs/KNOWN_LIMITATIONS.md`
