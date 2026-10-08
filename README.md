# OutcomeOS v1.3 — Decision Intelligence Powered by Panta

**OutcomeOS is a full-stack decision-memory app:** collaborative forecast workspaces, evidence journals, Panta prediction-market discovery and quotes, saved signal history, Brier calibration, risk scenarios, secure sharing and exports. Panta use is **strictly read-only**—no trades or fund custody.

This package includes **free public deployment support without buying a VPS or domain**: Render Web Service + Neon PostgreSQL. The actual service can only be published after you connect your own accounts and set private environment variables.

## Quick start: localhost

Python 3.10+; no package installation required for SQLite mode.

```sh
python main.py
```

Open `http://127.0.0.1:8766/` for the public landing page; choose **Open app** or visit `http://127.0.0.1:8766/app` directly. Create a user account.

For real market discovery, set a **fresh, private** `PANTA_API_KEY` in your local shell before starting. Run `python -m app.check_panta` for basic connectivity. No Panta key should be placed in source files or sent by chat. When the key is absent, market API requests explicitly fail rather than fabricating responses.

### Free cloud hosting

See **[`docs/DEPLOY_FREE_EN.md`](docs/DEPLOY_FREE_EN.md)**. Use `render.yaml` in your GitHub repository; Render prompts for the two **secret** values `DATABASE_URL` (Neon) and `PANTA_API_KEY` (new live key). The Dockerfile installs PostgreSQL driver automatically. Cloud mode refuses to start without PostgreSQL to prevent silent data loss.

**Never deploy local SQLite on Render Free**: local files are wiped on restarts/sleep. The Neon adapter provides durable storage for users, forecasts, links and reports. Back up via the authenticated JSON export.

## User workflows

1. Register and create a private workspace; invite team members through expiring tokens.
2. Create measurable YES/NO decision questions, deadlines and downside context.
3. Submit forecasts and notes/evidence; activity is recorded.
4. Discover Panta markets, view actual quotes and link contracts only with compatible settlement definitions.
5. Compare team and observed market quotes; store historical snapshots; view drift and divergence alerts.
6. Resolve outcomes and score forecasts using Brier scores, export JSON/CSV, and share an anonymized report via revocable expiring URL.

**Live market data** and synthetic onboarding examples are always identified separately. Cloud mode disables synthetic onboarding examples by default. Panta market *prices* should not be treated as calibrated forecast probabilities, and no performance or traction claim is implied.

## Tests

```sh
python -m unittest discover -s tests -v
node --check web/app.js
node --check web/share.js
```

Test coverage includes multi-user HTTP flows, invitations, CSRF, permission boundaries, Panta adapter contract/validation, mocked live API fixtures, quote deduplication, public reports, database compatibility transformation and deploy config. **Tests do not prove that your real Neon/PostgreSQL instance or real Panta credential works**—follow the public deployment checklist and verify them against the live service.

## Sources, docs, and limitations

- Panta API: https://docs.panta.market/
- Sidetrack: https://superteam.fun/earn/listing/panta-api-side-track
- Colosseum hackathon: https://colosseum.com/worldsfair
- English submission copy: [`docs/SUBMISSION_EN.md`](docs/SUBMISSION_EN.md)
- Pitch/demo scripts: [`docs/VIDEOS_EN.md`](docs/VIDEOS_EN.md)
- Complete English submission kit: [`docs/ENGLISH_SUBMISSION_KIT/00_START_HERE.md`](docs/ENGLISH_SUBMISSION_KIT/00_START_HERE.md)
- Historic v1.2 preview/notes: [`docs/PUBLIC_PREVIEW.md`](docs/PUBLIC_PREVIEW.md)

**Security:** An earlier live Panta key was posted in a conversation and should be revoked before any production use. This repository contains no live secret. The application uses PBKDF2 password hashes, server-side session cookies, CSRF protection, HTTP security headers, workspace permissions, Panta response validation, and private credentials. It has **not** undergone a comprehensive security audit, paid vulnerability assessment, or externally observed production uptime test. Free hosting is for limited early usage/hackathon judging, not a commercial uptime guarantee.

**License:** MIT. No investment, trading or gambling recommendation is made.
