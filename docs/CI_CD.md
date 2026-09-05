# CI/CD — Phase 10B

GitHub Actions workflow: `.github/workflows/ci.yml` at the monorepo git root.
Jobs run with `working-directory: RecoveryPilot-AI`.

---

## What runs

On push and pull request:

1. **Backend job**
   - Checkout
   - Python 3.12 with pip cache
   - `astral-sh/setup-uv` with dependency cache
   - `uv sync --group dev`
   - `ruff check` on `apps/backend`, `services`, `integrations`, `shared`, `simulator`
   - `pytest apps/backend/tests` (`ACTION_SCHEDULER_ENABLED=false`, empty Sentry DSN)
   - `docker build -f docker/Dockerfile.backend`

2. **Frontend job**
   - pnpm via `packageManager` in `package.json`
   - Node 22 with pnpm store cache (`pnpm-lock.yaml`)
   - `pnpm install --filter frontend`
   - `pnpm --filter frontend typecheck` (`tsc -b`)
   - `pnpm --filter frontend build`

---

## Local equivalents

From `RecoveryPilot-AI/`:

```powershell
uv sync --group dev
uv run ruff check apps/backend services integrations shared simulator
$env:PYTHONPATH = "apps/backend;services/src;integrations/src;shared/src;simulator/src;.;database"
$env:ACTION_SCHEDULER_ENABLED = "false"
uv run pytest apps/backend/tests -q

pnpm --filter frontend typecheck
pnpm --filter frontend build
```

If `uv` is not on PATH, use `python -m pytest` with the same `PYTHONPATH`.

---

## Images

CI builds the backend image to prove the Dockerfile still compiles. It does
not push to a registry. Wire a deploy job later:

```yaml
docker tag recoverypilot-backend:$SHA $REGISTRY/recoverypilot-backend:$SHA
docker push $REGISTRY/recoverypilot-backend:$SHA
```

Frontend production images are built by `docker compose -f docker-compose.prod.yml`.

---

## Secrets in CI

Do not put Razorpay, Gemini, or Sentry secrets in the workflow. Tests use
placeholder keys from Settings defaults. Production deploys inject secrets
from the host environment or a secret manager, not from git.
