# Deploy OutcomeOS publicly for $0 — no VPS or custom domain

This setup deploys a real multi-user web app and a durable database, not a local-only screenshot. It does **not** deploy on your behalf: you must create accounts and paste credentials into their providers' secret settings.

## Hosting architecture

- **Render Free Web Service** serves OutcomeOS at your own `https://....onrender.com` address with HTTPS, no purchased domain. Render's free app sleeps after ~15 minutes of inactivity; first request can take roughly a minute to wake.
- **Neon Free PostgreSQL** persists users, decisions, forecasts, Panta linked markets, history and share reports across Render restarts. Neon has a free plan. Stay within provider limits.
- **Panta Live API** serves market discovery and prices. Your **NEW, rotated** secret is stored server-side only; the application is read-only and cannot trade.

**NEVER use SQLite on Render Free**: the app's local files reset on spin-down/deploy. This repository deliberately aborts startup if `DATABASE_URL` is missing on Render (`OUTCOMEOS_REQUIRE_POSTGRES=1`).

## Step 0 — Security

You previously shared a `pk_live_...` API credential in chat. **Revoke it now and generate a different key.** Do not paste any API key, Neon connection URL or password in a chat, GitHub README, screenshot, or commit. Keep secrets in Render's environment-variable form only.

## Step 1 — Create a GitHub repository

1. Extract the downloaded ZIP. The project root must contain `main.py`, `Dockerfile` and `render.yaml`.
2. Go to <https://github.com/new> and create a repository, e.g. `outcomeos-panta`. Do not select any starter README/license on GitHub if you'll push this existing source.
3. Open PowerShell in the extracted project folder and run:

```powershell
# Only run these inside your extracted OutcomeOS project directory.
git init
git add .
git commit -m "Submission-ready OutcomeOS v1.3"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/outcomeos-panta.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub login and authenticate to GitHub if asked. Check GitHub's repo file list **does not contain `.env`**, any database, or actual secret values.

## Step 2 — Create durable PostgreSQL at Neon

1. Open <https://console.neon.tech/>, sign up and create a project `outcomeos` in a region near Render.
2. Open project **Connect** and copy the PostgreSQL connection string (prefer pooled connection; the app makes brief connections per request). It resembles `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require`.
3. Store this string in your password manager. This is a **secret** because it includes your database password. If your URL does not say `sslmode=require`, append it using `?` or `&`, as appropriate.
4. Do **not** paste the connection URL in GitHub, screenshots or chat.

## Step 3 — Deploy through Render Blueprint

1. Open <https://dashboard.render.com/> and sign up/sign in.
2. Select **New → Blueprint** and connect/select the GitHub repository containing `render.yaml`.
3. Review the plan. `render.yaml` declares **one Free Web Service**. Do not inadvertently select a paid plan.
4. In the initial Blueprint secret form, set:

| Secret key | Value |
|---|---|
| `DATABASE_URL` | Your private Neon PostgreSQL connection string |
| `PANTA_API_KEY` | Your newly rotated, private Panta Live API key |

Other variables are already configured in `render.yaml`: `OUTCOMEOS_COOKIE_SECURE=1`, `OUTCOMEOS_SEED_EXAMPLES=0`, `OUTCOMEOS_REQUIRE_POSTGRES=1` and `OUTCOMEOS_HOST=0.0.0.0`.

5. Approve creation. Render builds the Docker image (installs `psycopg[binary]`), initializes tables on Neon and starts the service.
6. Copy **your actual** `https://<generated-service-name>.onrender.com` address from Render. Do not type a guessed address.
7. Visit that HTTPS address. The landing page should display. Click **Open app** / **Create workspace**.

If the Render app cannot connect to Neon, check: `DATABASE_URL` must be copied verbatim, TLS required, database still active, database region and any external allowlist. If setup is slow, wait for Neon auto-resume.

## Step 4 — Verify real end-to-end behavior

- [ ] `https://YOUR_RENDER_URL/api/health` returns JSON `{"status":"ok",...}`.
- [ ] `https://YOUR_RENDER_URL/` displays public landing page.
- [ ] `https://YOUR_RENDER_URL/app` displays the interactive OutcomeOS UI.
- [ ] Register a real user and confirm that the initial cloud workspace is **empty** (no fabricated forecasts).
- [ ] Create a decision with measurable YES/NO outcome, set a deadline, enter your own prediction and evidence.
- [ ] **Market intelligence → Live Panta → Fetch live markets** loads actual API results. Use **View quotes** on a real market.
- [ ] Link a real market **only if outcome/resolution conditions match your decision**. Do not link irrelevant markets merely to look integrated.
- [ ] Record at least one live market price, refresh it later, and inspect stored history.
- [ ] Generate **Share decision report** as workspace owner; open shared HTTPS link in incognito. Confirm no account name/email or private notes appear.
- [ ] Restart/redeploy the Render service once and verify Neon data still exists.
- [ ] Capture screen recording and screenshots with API keys and database URLs hidden.

**No live Panta or hosted PostgreSQL verification was performed by the development environment.** Do these checks before claiming live integration in your public submission.

## Pricing / reliability caveats

Render Free can spin down after 15 minutes. Cold starts are expected. Render may suspend free services at included usage limits; if you have a billing method, overages may be charged. Neon Free has usage, storage and compute limits. The app is read-only, but API calls may be subject to Panta's own quotas/fees (not independently verified). Free-tier configurations are suitable for a hackathon/public beta, not an uptime-guaranteed commercial product. Keep backups through the authenticated **Team & activity → JSON export** feature. All use must comply with Panta and hosting provider terms.

## After deployment

Use the **real Render URL** and your **actual GitHub URL** in both required submission portals:

- <https://colosseum.com/worldsfair>
- <https://superteam.fun/earn/listing/panta-api-side-track>

Full application code and explanation: `README.md`. English content for submissions: `docs/SUBMISSION_EN.md`. Video scripts: `docs/VIDEOS_EN.md`.
