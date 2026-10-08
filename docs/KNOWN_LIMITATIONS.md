# What is and isn't verified

## Implemented and locally tested

- Public landing + local hosted application and routes (HTTP smoke)
- Team accounts, sessions, CSRF, private workspace permissions, decisions, forecasts, evidence, sharing and exports
- Panta discovery/detail adapter and simulated local HTTP fixture verifying `X-Api-Key` and response validation
- Brier scoring, market quote snapshots and deduplication
- PostgreSQL SQL-compatibility adapter and schema translation (offline tests only)
- Render YAML secret-only configuration and Docker image build instructions
- More than 30 automated tests; JavaScript syntax checks

## User verification required before honest submission

- Actual Neon PostgreSQL database connection and write/read durability after service restart
- Actual Render public HTTPS deployment and password/cookie/security behavior behind reverse proxy
- A newly rotated Panta key and matching real market quote returned via Render (earlier user's screenshot showed live catalog results in prior v1.1, not necessarily in this cloud release)
- Browser walkthrough with screenshot/video on the real site (this environment blocked browser access to localhost)
- Full security review, including authentication abuse protections and rate limiting
- Colosseum account, actual GitHub repo, presentation and demonstration recordings, and separate official submissions

## Product scope

OutcomeOS is a **functional beta**, not a full regulated trading platform. It does not create prediction markets, trade, sign transactions, custody assets, offer investment guidance, or guarantee decision accuracy. Free hosting has cold starts and resource limits; email verification, billing, infrastructure observability, professional security audit, backup automation and uptime SLA are not included. Backend worker quote syncing is opt-in on persistent hosting; Render Free only supports on-demand/manual refresh when active (background scheduling is not guaranteed).
