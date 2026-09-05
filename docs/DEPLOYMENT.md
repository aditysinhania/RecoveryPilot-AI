# Deployment — Phase 10B

Production packaging for RecoveryPilot AI. Domain engines (diagnosis, policy,
planner, executor, orchestrator, simulator, webhook ingest) are unchanged.

---

## Topology

```
browser → nginx:80
            ├─ /api, /metrics, /docs  → backend:8000
            └─ /                      → frontend:80 (SPA)
backend → postgres:5432
         → redis:6379 (provisioned; not required by recovery logic)
```

Compose file: `docker-compose.prod.yml`. Images: `docker/Dockerfile.backend`,
`docker/Dockerfile.frontend`. Edge proxy: `docker/nginx.prod.conf`.

---

## Required environment

Copy `.env.example` to `.env` and set real values for production.

| Variable | Role |
| --- | --- |
| `APP_ENV` | `production` in Compose prod |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Sandbox keys (live `rzp_live_` rejected) |
| `RAZORPAY_WEBHOOK_SECRET` | HMAC for `POST /api/v1/webhooks/razorpay` |
| `GEMINI_API_KEY` | Leave placeholder to stay on local fallback copy |
| `SENTRY_DSN` | Empty disables Sentry |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0`–`1.0` |
| `APP_VERSION` / `BUILD_SHA` | Shown on Operations Status |
| `REDIS_URL` | `redis://redis:6379/0` in prod Compose |
| `CORS_ORIGINS` | Public origin (the nginx host) |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,backend,nginx,frontend` plus your DNS name |

Never commit real secrets. Placeholder Razorpay keys keep the Sandbox client
in mock mode so containers boot without a Razorpay account.

---

## Run production Compose

From `RecoveryPilot-AI/`:

```powershell
copy .env.example .env
docker compose -f docker-compose.prod.yml up --build
```

- App: `http://localhost/` (or `HTTP_PORT`)
- API: `http://localhost/api/v1/live`
- Metrics: `http://localhost/metrics`
- OpenAPI: `http://localhost/docs`

Postgres is not published on the host in prod Compose. Back up the
`postgres_data` volume.

Local development still uses `docker compose up postgres` plus Vite on 5173
and uvicorn on 8000. See the root README.

---

## Health used by orchestrators

| Probe | Path | Restart vs ready |
| --- | --- | --- |
| Liveness | `GET /api/v1/live` | Process up. No Postgres. |
| Readiness | `GET /api/v1/ready` | 503 if Postgres is down. |
| Combined | `GET /api/v1/health` | Always 200; `data.database` is `connected` or `unavailable`. |

Backend image `HEALTHCHECK` uses `/api/v1/live` so a temporary Postgres blip
does not recreate the API container.

---

## Webhooks

Point the Razorpay dashboard at:

```
https://<your-host>/api/v1/webhooks/razorpay
```

Use the same `RAZORPAY_WEBHOOK_SECRET`. Invalid signatures are 401 and are
not stored.

---

## Frontend build args

The frontend image bakes:

- `VITE_API_BASE_URL=/api/v1` (same-origin through nginx)
- `VITE_APP_VERSION` / `VITE_BUILD_SHA` for the Operations page

Rebuild the frontend image after changing those args.
