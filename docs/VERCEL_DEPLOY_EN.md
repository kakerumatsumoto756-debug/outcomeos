# Vercel deployment for OutcomeOS

The original local server uses `ThreadingHTTPServer`. The new `vercel_wsgi.py` adapts the existing handler to a WSGI application exported as `app` from `main.py` (explicit `tool.vercel.entrypoint`). No external listening port is needed on Vercel. Neon remains the source of durable data.

Deployment steps: connect the GitHub repository in https://vercel.com/new (Hobby for eligible non-commercial personal demonstrations), add `DATABASE_URL` for the Neon PostgreSQL database and a NEW `PANTA_API_KEY` secret, and deploy. The Vercel runtime forces `OUTCOMEOS_REQUIRE_POSTGRES=1`, `OUTCOMEOS_COOKIE_SECURE=1`, `OUTCOMEOS_SEED_EXAMPLES=0`.

After deployment, check `/`, `/api/health`, `/app`, registration, forecast creation, and live Panta market prices. Do not include secrets in code, README, ZIP, or Git history.

Not yet verified: deployment on Vercel, real Neon integration and live Panta requests. Hobby plan terms restrict use to non-commercial personal work; confirm award-eligible hackathon use with the host.
