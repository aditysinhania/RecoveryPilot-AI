# RecoveryPilot AI architecture

This note maps folders to responsibilities. Development commands live in the root [README](../README.md).

## Runtime flow

```
Merchant UI (apps/frontend)
        │  /api
        ▼
FastAPI routers (apps/backend/app/api)
        │
        ▼
Domain services (services/)
        │
        ├── shared/         types and constants
        ├── integrations/   Razorpay, messaging, LLM
        ├── database/       PostgreSQL via SQLAlchemy
        └── simulator/      batch recovery evaluation
```

## Package boundaries

| Path | Owns |
| --- | --- |
| `apps/frontend` | React UI only |
| `apps/backend` | HTTP, auth wiring, ORM models, Pydantic schemas, DB session |
| `services` | Diagnosis, policy, recovery orchestration |
| `integrations` | Third-party HTTP clients |
| `shared` | Cross-cutting types and constants |
| `simulator` | Synthetic batches and measured-recovery reports |
| `database` | SQLAlchemy models, Alembic, Postgres init, seed scaffolding |
| `docker` | Container images and nginx |

Routers stay thin. Services never call third parties directly; they go through `integrations`.
