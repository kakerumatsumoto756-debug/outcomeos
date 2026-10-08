# OutcomeOS v1.2 — public HTTPS preview deployment

**Purpose:** Deploy a limited, publicly reachable hackathon preview for invited judges. This is **not** a security-audited commercial SaaS deployment. A public website requires a server/VPS, a domain with DNS pointed at that server, open 80/443, Docker Compose, and a newly rotated Panta API key.

## Before you deploy

1. **Revoke any Panta key that was pasted into chat.** Generate a new live key with the minimum permissions Panta supports. Never commit it, paste it into a ticket, or include it in screenshots.
2. Confirm the [Panta terms](https://docs.panta.market/) allow the intended type of API redisplay and usage. This app is intentionally read-only; it never signs a wallet transaction or trades.
3. Use a VPS you control. Do not expose the application itself directly; only Caddy should face the internet.
4. This preview has no email verification, backups, provider-independent rate limiting, security audit, or hardened multi-tenant operations. Do not onboard strangers or collect sensitive forecasts without further security work.

## Start the HTTPS preview

On the VPS, in the extracted project folder, create `.env` locally:

```ini
SITE_DOMAIN=outcomeos.your-own-domain.com
PANTA_API_KEY=NEWLY_ROTATED_KEY_SET_LOCALLY
PANTA_API_BASE=https://live-api.panta.market/api/v1
```

The example values are placeholders. `.env` is gitignored and intentionally **not provided** with the download. Point the DNS A/AAAA record at the VPS IP, allow inbound ports 80 and 443, then:

```bash
docker compose --env-file .env -f compose.public.yaml up -d --build
```

Caddy obtains HTTPS certificates automatically when DNS and networking permit. Test:

```bash
curl -fsS https://outcomeos.your-own-domain.com/api/health
```

Visit the HTTPS URL, sign up and create a truthful decision room. The public preview disables automatic synthetic sample decisions. Choose a question that genuinely corresponds to one of the Panta markets, quote the matching settlement condition and deadline, and link the Panta market using `Market intelligence`.

To enable opt-in background price snapshots (15-minute default; respect provider quotas), use:

```bash
docker compose --env-file .env -f compose.public.yaml --profile live-sync up -d --build
```

Check `/api/panta/check` using the *Test Panta connection* button inside the authenticated application. This makes a read-only live catalog request and validates permission for that endpoint; it does not confirm all other endpoints or live data provenance.

## Share a real evidence-backed decision with a judge

1. Open the decision room while signed in as a workspace **owner**.
2. Choose **Share decision report**. Review the fields to be published.
3. Click **Create share link** and copy the generated `https://.../share?t=...` link.
4. Open in an incognito browser and verify the published information. Users do **not** need to sign up.
5. The report expires after **7 days**, can be revoked by the owner, and creating a new link invalidates the old one.

Anonymous reports expose ONLY the decision's title, question, description, category, status, aggregated latest team forecast, deadline/outcome and linked market title, documented match explanation, source, and saved quote history. They do not expose individual names, emails, raw individual forecasts, private evidence notes, workspaces or API credentials. **Anyone holding the link can read its published contents**—do not share sensitive decisions.

**Historical quotes are not a live price stream.** A shared report can contain 0 stored points until the market was linked and refreshed. An accurate judge demonstration should show the recorded timestamps and verify that the markets are genuinely compatible with each decision's outcome definition. Demo-source markets are prominently labeled.

## Security and operations still required before commercial public launch

- Provider-side key rotation and least-privilege API key
- Security audit, stricter public rate limits, CSRF/headers checks in real browser and reverse-proxy integration tests
- User registration controls, verified emails, password resets, access governance and account lifecycle
- Monitoring, backups and recovery tests, database migrations, resource limits, service telemetry
- Real browser end-to-end tests including mobile, deployment on an actual VPS with DNS/TLS, and provider quota/cost confirmation
- Privacy policy, terms of service, applicable market-data and financial regulations

## Stop/restart

```bash
docker compose --env-file .env -f compose.public.yaml ps
docker compose --env-file .env -f compose.public.yaml logs --tail 50 outcomeos
docker compose --env-file .env -f compose.public.yaml down
```

Do not use `down -v` unless you intentionally want to remove your stored data.

## Upgrading an existing local SQLite database

Stop the old Python server and background poller completely. Back up the old `data/` directory. Move a copy of that entire directory under the newly extracted `outcomeos/` root **while all processes are stopped**, and then start the new version. New `public_reports` tables are added with `CREATE TABLE IF NOT EXISTS`; existing decisions are retained. Docker volumes require separate volume backup/restore. Do not copy only the main `.sqlite3` file while it is in use (WAL may contain uncheckpointed transactions).
