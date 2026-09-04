# Backend architecture — Phase 4C

FastAPI backend for RecoveryPilot AI (Razorpay Hackathon Track 03).
Phase 4A delivered the HTTP foundation. Phase 4B added read-only merchant
dashboard APIs. Phase 4C adds the **recovery queue** that powers Payments
Requiring Attention. There is still **no** diagnosis, planner, Razorpay call,
Gemini, scheduler, or payment execution.

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
│       ├── recovery.py     # queue, case, timeline, summary (thin)
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
│   ├── merchant_dashboard.py
│   └── recovery.py         # RecoveryQueueItem, case, timeline, summary
├── services/
│   ├── merchant_service.py # HTTP adapter; maps ORM → Pydantic, 404
│   └── recovery_service.py # HTTP adapter for the recovery queue
└── utils/                  # pagination (PageMeta), request_id, time

services/src/services/
├── merchant_service.py     # merchant dashboard SQLAlchemy queries
└── recovery_service.py     # recovery queue SQLAlchemy queries
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

## Recovery API flow

```mermaid
sequenceDiagram
    participant Client
    participant Router as /api/v1/recovery
    participant Adapter as app.services.recovery_service
    participant Domain as services.recovery_service
    participant PG as PostgreSQL

    Client->>Router: GET /queue?status=&page=
    Router->>Router: Depends(get_db), normalize_page
    Router->>Adapter: get_recovery_queue(...)
    Adapter->>Domain: parse_queue_filters
    Adapter->>Domain: get_recovery_queue(db, filters, offset, limit)
    Domain->>PG: JOIN recovery_cases, payments, customers
    PG-->>Domain: page + COUNT(*)
    Domain-->>Adapter: QueuePageResult
    Adapter-->>Router: list[RecoveryQueueItem]
    Router-->>Client: PaginatedResponse
```

| Route | Service call | Envelope |
| --- | --- | --- |
| `GET /api/v1/recovery/queue` | `get_recovery_queue` | `PaginatedResponse[RecoveryQueueItem]` |
| `GET /api/v1/recovery/cases/{recovery_case_id}` | `get_recovery_case` | `ApiResponse[RecoveryCaseResponse]` |
| `GET /api/v1/recovery/cases/{recovery_case_id}/timeline` | `get_recovery_timeline` | `ApiResponse[list[RecoveryTimelineEvent]]` |
| `GET /api/v1/recovery/summary` | `get_recovery_summary` | `ApiResponse[RecoverySummaryResponse]` |

Unknown `recovery_case_id` returns HTTP 404 `recovery_case_not_found`.

---

## Queue filtering flow

```mermaid
flowchart TD
    Q[Query params] --> P[parse_queue_filters]
    P -->|bad enum / date / priority| F[invalid_filter 400]
    P -->|date_from after date_to| D[invalid_date_range 400]
    P --> N[normalize_page]
    N --> SQL[JOIN cases + payments + customers]
    SQL --> W{WHERE}
    W --> S[status = RecoveryStatus]
    W --> R[failure_reason on payment or diagnosis]
    W --> C[customer_segment]
    W --> PR[priority band or min score]
    W --> M[payment_method]
    W --> DT[payment.created_at between date_from and date_to]
    W --> MID[optional merchant_id]
    SQL --> ORD["ORDER BY priority_score DESC NULLS LAST, payment.created_at ASC"]
    ORD --> PAGE[OFFSET / LIMIT]
    PAGE --> META[total_records, total_pages, has_next, has_previous]
```

`priority` accepts `HIGH` (≥ 0.8), `MEDIUM` (0.6–0.8), `LOW` (< 0.6), or a numeric minimum score.

---

## Recovery case lifecycle

```mermaid
stateDiagram-v2
    [*] --> OPEN: payment failed, case opened
    OPEN --> DIAGNOSED: diagnosis fields stored
    DIAGNOSED --> WAITING_RETRY: retry / payday wait scheduled
    DIAGNOSED --> WAITING_PROMISE: promise-to-pay recorded
    WAITING_RETRY --> RECOVERED: payment captured
    WAITING_RETRY --> ESCALATED: policy or playbook escalate
    WAITING_RETRY --> STOPPED: stop recovery
    WAITING_PROMISE --> RECOVERED: promise fulfilled
    WAITING_PROMISE --> WAITING_RETRY: promise broken, retry
    WAITING_PROMISE --> STOPPED: stop recovery
    ESCALATED --> RECOVERED: agent recovered
    ESCALATED --> STOPPED: agent stopped
    RECOVERED --> CLOSED: case closed
    STOPPED --> CLOSED: case closed
```

Timeline events (ascending `occurred_at`): payment failed → diagnosis created → actions scheduled/executed → webhook updates → audit summaries. This phase **reads** those rows; it does not run diagnosis, policy, or Razorpay.

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

## Recovery service layer

```mermaid
flowchart TB
    R[recovery.py router]
    A[app/services/recovery_service.py adapter]
    D[services/recovery_service.py]
    RC[(recovery_cases)]
    P[(payments)]
    C[(customers)]
    S[(subscriptions)]
    RA[(recovery_actions)]
    PTP[(promises_to_pay)]
    AL[(audit_logs)]
    WH[(webhook_events)]

    R -->|"Depends(get_db)"| A
    A -->|map 404 / filters / Pydantic| D
    D --> RC
    D --> P
    D --> C
    D --> S
    D --> RA
    D --> PTP
    D --> AL
    D --> WH
```

- **`services.recovery_service`**: `get_recovery_queue`, `get_recovery_case`, `get_recovery_timeline`, `get_recovery_summary`. Raises domain `RecoveryCaseNotFoundError`, `InvalidFilterError`, `InvalidDateRangeError`.
- **`app.services.recovery_service`**: Maps those onto HTTP exceptions and dashboard DTOs. Never returns ORM.
- Webhooks have no FK; timeline matches `payload.payload.payment.entity.id` to `payments.razorpay_payment_id`. Audit events are **summaries only** (`event_summary`, type, actor) — the audit router is unchanged.

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
| `RecoveryNotFoundError` | 404 | `recovery_case_not_found` |
| `InvalidFilterError` | 400 | `invalid_filter` |
| `InvalidDateRangeError` | 400 | `invalid_date_range` |
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

Paginated success adds `page`, `page_size`, `total`, `total_records`, `total_pages`, `has_next`, and `has_previous`. `utils/pagination.py` (`normalize_page`, `build_page_meta`) is the reusable helper.

Builders: `success_body`, `paginated_body`, `error_body`, `error_response` in
`app/core/responses.py`. Generic models live in `app/schemas/common.py`.

---

## OpenAPI

- Title: **RecoveryPilot AI Backend**
- Description: AI Revenue Recovery Agent for Razorpay Track 03
- Tags: Health, Merchants, Recovery, Audit, Simulator
- Docs: `/docs` · ReDoc `/redoc` · schema `/openapi.json`

Recovery queue routes query PostgreSQL. Audit and simulator routers remain placeholders. Merchant dashboard routes query PostgreSQL.

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
| `test_recovery.py` | Queue paths registered; `invalid_filter` / `invalid_date_range`; case 404 when Postgres is up |
| `test_pagination.py` | `normalize_page` clamps size; `build_page_meta` computes pages and cursors |
| `test_settings.py` | Settings load; `get_settings` is cached; illegal `APP_ENV` rejected |
| `test_database.py` | Engine and `get_db` initialize without a live query |
