# Backend architecture — Phase 4B

FastAPI backend for RecoveryPilot AI (Razorpay Hackathon Track 03).
Phase 4A delivered the HTTP foundation. Phase 4B adds **read-only merchant
dashboard APIs** and small infrastructure tightening. There is still **no**
diagnosis, planner, Razorpay call, Gemini, or payment execution.

Run locally:

```powershell
uv run uvicorn app.main:app --reload --app-dir apps/backend
```

OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs) · ReDoc `/redoc`.

---

## Folder map

```
apps/backend/app/
├── main.py                 # app = create_app() only
├── api/
│   ├── deps.py             # session, settings, request_id, correlation_id, logger
│   └── v1/
│       ├── router.py       # central /api/v1 registration
│       ├── health.py       # /live, /ready, /health, /health/database
│       ├── merchants.py    # dashboard (thin; no SQL)
│       ├── recovery.py     # placeholders
│       ├── audit.py        # placeholders
│       └── simulator.py    # placeholders
├── config/
│   ├── settings.py         # Pydantic BaseSettings; get_settings() is @lru_cache
│   ├── logging.py          # JSON logger factory (request_id + correlation_id)
│   ├── constants.py
│   └── environment.py
├── core/
│   ├── lifespan.py         # create_app(), lifespan, exception handlers
│   ├── middleware.py       # TrustedHost → CORS → GZip → IDs → timing → logs
│   ├── exceptions.py
│   └── responses.py        # ApiResponse / PaginatedResponse / ErrorResponse
├── db/                     # engine, get_db, SELECT 1
├── schemas/
│   ├── common.py           # ApiResponse[T], PaginatedResponse[T], ErrorResponse
│   └── merchant_dashboard.py
├── services/
│   └── merchant_service.py # HTTP adapter; maps ORM → Pydantic, 404
└── utils/

services/src/services/
└── merchant_service.py     # all merchant dashboard SQLAlchemy queries
```

Canonical ORM tables remain in `database/models/`. Domain queries live in
`services/`. Routers only parse parameters, call the adapter, and wrap envelopes.

---

## API flow

```mermaid
sequenceDiagram
    participant Client
    participant MW as Middleware stack
    participant Router as /api/v1/merchants
    participant Adapter as app.services.merchant_service
    participant Domain as services.merchant_service
    participant PG as PostgreSQL

    Client->>MW: GET /api/v1/merchants/{id}/summary
    MW->>MW: TrustedHost, CORS, GZip
    MW->>MW: request_id + correlation_id
    MW->>MW: timing + access log
    MW->>Router: Depends(get_db), logger
    Router->>Adapter: get_summary(db, merchant_id)
    Adapter->>Domain: load_summary(db, merchant_id)
    Domain->>PG: SELECT merchant + COUNT(*) + metrics
    PG-->>Domain: rows
    Domain-->>Adapter: MerchantSummaryResult
    Adapter-->>Router: MerchantSummary (Pydantic)
    Router-->>Client: ApiResponse + X-Request-ID + X-Correlation-ID
```

| Route | Service call | Envelope |
| --- | --- | --- |
| `GET /api/v1/merchants/{merchant_id}/summary` | `get_summary` | `ApiResponse[MerchantSummary]` |
| `GET /api/v1/merchants/{merchant_id}/metrics` | `get_metrics` | `ApiResponse[MerchantMetricsPayload]` |
| `GET /api/v1/merchants/{merchant_id}/payments` | `list_payments` | `PaginatedResponse[PaymentListItem]` |
| `GET /api/v1/merchants/{merchant_id}/failures` | `list_failures` | `PaginatedResponse[FailureListItem]` |

Payments and failures accept `page` (1-based) and `page_size` (clamped to 100).
Unknown `merchant_id` returns HTTP 404 `merchant_not_found`.

---

## Merchant service layer

```mermaid
flowchart TB
    R[merchants.py router]
    A[app/services/merchant_service.py adapter]
    D[services/merchant_service.py]
    M[(merchants)]
    C[(customers)]
    S[(subscriptions)]
    P[(payments)]
    RC[(recovery_cases)]
    MM[(merchant_metrics)]

    R -->|"Depends(get_db)"| A
    A -->|map 404 / Pydantic| D
    D --> M
    D --> C
    D --> S
    D --> P
    D --> RC
    D --> MM
```

- **`services.merchant_service`**: SQLAlchemy `select` / `func.count` / `db.get`.
  Raises domain `MerchantNotFoundError`. Returns ORM + counts.
- **`app.services.merchant_service`**: Catches the domain miss, raises
  `app.core.exceptions.MerchantNotFoundError` (HTTP 404), builds dashboard DTOs.
  Metrics with no snapshot row become zeros, not 404.
- Failures are `payment_status = FAILED`, newest `created_at` first, left-joined
  to `recovery_cases` for `recovery_status`.

---

## Request → Service → Database

```mermaid
flowchart LR
    REQ[HTTP request] --> DEP["Depends(get_db)"]
    DEP --> SESS[SQLAlchemy Session]
    REQ --> RT[Thin router]
    RT --> SVC[merchant_service]
    SVC --> SESS
    SESS --> PG[(PostgreSQL)]
    SVC --> DTO[Pydantic DTO]
    DTO --> ENV[ApiResponse / PaginatedResponse]
    ENV --> RES[JSON response]
```

Routers never return ORM objects. Money stays integer paise.

---

## Request lifecycle (middleware)

Starlette applies middleware in reverse registration order. **Last added is outermost.**

Request flow (outer → inner):

**TrustedHost → CORS → GZip → Request ID → Request Timing → Structured Logging → Exception Handling → route**

```mermaid
flowchart TB
    TH[TrustedHostMiddleware]
    CORS[CORSMiddleware]
    GZ[GZipMiddleware]
    RID[RequestIdMiddleware]
    TIME[RequestTimingMiddleware]
    LOG[StructuredLoggingMiddleware]
    EX[Exception handlers]
    APP[Route handlers]
    TH --> CORS --> GZ --> RID --> TIME --> LOG --> EX --> APP
```

| Middleware | Role |
| --- | --- |
| Trusted Host | Hosts from `TRUSTED_HOSTS` |
| CORS | Origins from `CORS_ORIGINS`; exposes `X-Request-ID` and `X-Correlation-ID` |
| GZip | Bodies over 500 bytes |
| Request ID | `request_id` from `X-Request-ID` or a new UUID; `correlation_id` from `X-Correlation-ID` or the same as `request_id` |
| Timing | `latency_ms` + `X-Response-Time-Ms` |
| Structured logging | JSON access log: method, path, status, latency, both ids |
| Exception handling | Standard `ErrorResponse` envelope |

Every success or error body includes `request_id`, `correlation_id`, and `timestamp`.

---

## Dependency injection

```mermaid
flowchart LR
    EP[Endpoint]
    EP --> RID[request_id_dep]
    EP --> CID[correlation_id_dep]
    EP --> SET["get_settings @lru_cache"]
    EP --> DB[get_db]
    EP --> LOG[logger_dep]
    EP --> MER[get_current_merchant]
    DB --> ENG[get_engine]
    ENG --> PG[(PostgreSQL)]
    MER --> NONE[None until auth]
```

`Settings()` is constructed once via `get_settings()` (`@lru_cache(maxsize=1)`).

---

## Application startup

```mermaid
flowchart TD
    A[create_app] --> B[configure_logging]
    B --> C[FastAPI metadata / OpenAPI tags]
    C --> D[register_middleware]
    D --> E[register_exception_handlers]
    E --> F[include_router API_PREFIX]
    F --> G[lifespan startup]
    G --> H[validate_environment]
    H --> I[get_engine]
    I --> J{ping_database}
    J -->|ok| K[serve]
    J -->|fail and production| L[raise DatabaseUnavailableError]
    J -->|fail and local/dev| M[log warning and serve]
```

Shutdown disposes the SQLAlchemy pool and logs `app.shutdown`.

Environment must be one of `local`, `development`, `staging`, `production`.
`DATABASE_URL` and `API_VERSION` are required. Secrets are never written to logs.

---

## Logging

JSON lines to stdout via `JsonLogFormatter`:

| Field | Source |
| --- | --- |
| timestamp | UTC ISO-8601 |
| level | INFO / DEBUG / WARNING / ERROR |
| logger | logger name |
| message | log message |
| environment | `APP_ENV` |
| request_id | contextvar or record extra |
| correlation_id | contextvar or record extra |
| method, path, status_code, latency_ms | access middleware extras |

---

## Health

| Method | Path | Meaning |
| --- | --- | --- |
| GET | `/api/v1/live` | Process liveness. Always 200. No database call. |
| GET | `/api/v1/ready` | Readiness. 200 if Postgres answers `SELECT 1`, else 503. |
| GET | `/api/v1/health` | Combined. Always 200. `data.database` is `connected` or `unavailable`. |
| GET | `/api/v1/health/database` | Same check as `/ready`. |

Docker `HEALTHCHECK` and Compose use `/api/v1/health`.

---

## Error handling

All failures use:

```json
{
  "success": false,
  "error": "...",
  "code": "...",
  "request_id": "...",
  "correlation_id": "...",
  "timestamp": "..."
}
```

| Exception | HTTP | Code |
| --- | --- | --- |
| `DatabaseUnavailableError` | 503 | `database_unavailable` |
| `MerchantNotFoundError` | 404 | `merchant_not_found` |
| `RecoveryNotFoundError` | 404 | `recovery_not_found` |
| `PolicyViolationError` | 403 | `policy_violation` |
| `ValidationException` / `RequestValidationError` | 422 | `validation_error` |
| `ApplicationException` | mapped | mapped |
| Unhandled | 500 | `internal_error` |

Success:

```json
{
  "success": true,
  "message": "ok",
  "data": {},
  "request_id": "...",
  "correlation_id": "...",
  "timestamp": "..."
}
```

Paginated success adds `page`, `page_size`, and `total`.

Builders: `success_body`, `paginated_body`, `error_body`, `error_response` in
`app/core/responses.py`. Generic models live in `app/schemas/common.py`.

---

## OpenAPI

- Title: **RecoveryPilot AI Backend**
- Description: AI Revenue Recovery Agent for Razorpay Track 03
- Tags: Health, Merchants, Recovery, Audit, Simulator
- Docs: `/docs` · ReDoc `/redoc` · schema `/openapi.json`

Recovery, audit, and simulator routers remain placeholders. Merchant dashboard
routes query PostgreSQL.

---

## Tests

```powershell
cd apps/backend
uv run pytest
```

| File | Asserts |
| --- | --- |
| `test_health.py` | `/live` and `/health` are 200; request and correlation ids echo |
| `test_merchants.py` | Dashboard paths are registered; unknown UUID is 404 when Postgres is up |
| `test_settings.py` | Settings load; `get_settings` is cached; illegal `APP_ENV` rejected |
| `test_database.py` | Engine and `get_db` initialize without a live query |
