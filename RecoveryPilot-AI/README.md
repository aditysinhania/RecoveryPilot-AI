# RecoveryPilot AI

Monorepo for the Razorpay AI Buildathon **Track 03: AI Revenue Recovery**.

RecoveryPilot detects revenue at risk (failed payments, mandate failures, overdue receivables), chooses a bounded intervention, executes it, and records an audit trail. This repository is the scaffold: apps, shared packages, Postgres, and Docker. Domain logic is not implemented yet.

## Architecture

```
apps/frontend          React + Vite + TailwindCSS + TypeScript
apps/backend           FastAPI (Python 3.12) — routers, models, schemas, config, DB session
services/              Business logic (diagnosis, policy, recovery)
integrations/          External APIs (Razorpay, messaging, LLM)
shared/                Cross-cutting types and constants
simulator/             Batch recovery simulator and evaluation harness
database/              Alembic migrations + Postgres init
docker/                Dockerfiles and nginx
docs/                  Architecture notes
```

Request path:

```
UI  →  FastAPI router  →  services/  →  integrations/ + PostgreSQL
                 │              └── simulator/ (batch runs)
                 └── shared/
```

Routers stay thin. SQLAlchemy models and Pydantic schemas live under `apps/backend/app/`. Recovery rules belong in `services/`, never in the UI or in routers.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React, Vite, TailwindCSS, TypeScript, pnpm |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x |
| Validation | Pydantic v2 |
| Python packages | uv workspace (pip editable installs as fallback) |
| Containers | Docker Compose at the monorepo root |

## Prerequisites

- Node.js 22+ and [pnpm](https://pnpm.io) 11+
- Python 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker Desktop (optional, for Compose)
- PostgreSQL 16 if you are not using Compose for the database

Install uv on Windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If `uv` is not on PATH after a pip install, use `python -m uv` in place of `uv`.

## Local development

From this `RecoveryPilot-AI` directory:

```powershell
copy .env.example .env
```

### 1. Database

```powershell
docker compose up postgres
```

Or point `DATABASE_URL` in `.env` at a local Postgres instance. Default credentials match `.env.example`.

Migrations (after models exist):

```powershell
python -m uv run alembic -c database/alembic.ini upgrade head
```

### 2. Backend

With uv (preferred):

```powershell
python -m uv sync
python -m uv run uvicorn app.main:app --reload --app-dir apps/backend --host 0.0.0.0 --port 8000
```

With pip:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e apps/backend -e services -e integrations -e simulator -e shared
pip install -r apps/backend/requirements.txt
uvicorn app.main:app --reload --app-dir apps/backend --host 0.0.0.0 --port 8000
```

Health check: `http://localhost:8000/api/health`

### 3. Frontend

```powershell
pnpm install
pnpm dev:frontend
```

Vite serves `http://localhost:5173` and proxies `/api` to the FastAPI process.

## Docker (full stack)

```powershell
docker compose up --build
```

- UI: `http://localhost:8080`
- API: `http://localhost:8000`
- Postgres: `localhost:5432`

## Layout rules

- **Do not** put business logic in `apps/backend/app/api` or `apps/frontend`.
- **Do** add FastAPI routers under `apps/backend/app/api/` and register them in `apps/backend/app/main.py`.
- **Do** keep third-party HTTP in `integrations/`.
- **Do** keep batch evaluation in `simulator/`.
- **Do** keep shared types in `shared/`.
- JSON responses stay explicit (`status`, and `code` / `message` on errors). Never return ORM objects.

## Current bootstrap

The API exposes `/api/health` only. Shared packages export empty modules so the workspace installs cleanly. Next work is domain models, recovery services, and the merchant UI.
