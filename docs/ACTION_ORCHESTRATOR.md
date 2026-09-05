# Action Orchestrator — Phase 9B

Production-style execution of RecoveryPlans against **Razorpay Sandbox**.
Diagnosis, policy, and planner engines are unchanged. Simulator datasets and
database relationships / PostgreSQL enums are unchanged.

Razorpay HTTP lives in `integrations/razorpay/`. Domain flow lives in
`services/action_orchestrator/`, `services/scheduler/`,
`services/communications/`, and `services/razorpay_actions/`.

---

## What it does

1. Load the case, call existing `evaluate_case` + `plan_case` (read-only engines).
2. Gate on policy decision, cooldown, and blocked channels.
3. Create a `recovery_actions` row (existing table) with a deterministic
   execution id and idempotency key `exec:{case}:{strategy}:{scheduled_at}`.
4. Call Razorpay Sandbox:
   - `SEND_PAYMENT_LINK` / `SWITCH_PAYMENT_METHOD` → Payment Links API
   - `REQUEST_NEW_MANDATE` → mandate/card-update session (Payment Links + purpose)
   - `RETRY_PAYMENT` / `RETRY_SILENTLY` → Orders API (retry request)
   - `WAIT_FOR_PAYDAY` / `HONOUR_PROMISE_TO_PAY` → scheduler until `scheduled_at`
5. Notify via sandbox SMS / WhatsApp / Email mocks (never live carriers).
   `RETRY_SILENTLY` skips customer notify.
6. Append `audit_logs` with `request_id` and `correlation_id` in JSON.
7. Transient Sandbox/comms failures back off **1m±15s → 5m±45s → 30m±2m → 2h±5m**,
then dead-letter. Attempt count is unchanged (four retries, then dead-letter).

Placeholder Razorpay keys stay in **mock Sandbox mode** so local/CI never
needs a real Razorpay account. `rzp_live_` keys are rejected.

---

## Status mapping

Merchant-facing lifecycle uses existing `ExecutionStatus` values:

| Display | Stored as |
| --- | --- |
| SCHEDULED | `SCHEDULED` |
| SENT | `RUNNING` + `metadata.display_status=SENT` |
| SUCCESS | `SUCCEEDED` |
| FAILED | `FAILED` |
| CANCELLED | `CANCELLED` |
| EXPIRED | `SKIPPED` + `metadata.expired` |
| RETRYING | `SCHEDULED` + `metadata.retrying` |
| dead-letter | `FAILED` + `metadata.dead_lettered` |

Planner strategies map onto existing `RecoveryActionType` values (no new enum).

---

## HTTP

```
POST /api/v1/actions/{case_id}/execute
POST /api/v1/actions/{case_id}/schedule
GET  /api/v1/actions/{case_id}/status
POST /api/v1/actions/replay/{execution_id}
GET  /api/v1/actions/summary?merchant_id=
```

The summary route feeds dashboard KPIs and queue action chips. It does not
change `/recovery/*`.

A daemon tick (FastAPI lifespan) runs due `SCHEDULED` rows when
`ACTION_SCHEDULER_ENABLED=true` and Postgres is up. Tests set the flag false.
Due jobs persist in `scheduler_jobs` (no FKs onto `recovery_actions` or
`recovery_cases`). The in-memory store is tests-only.

The summary JSON adds `scheduler_queue` (`scheduled`, `running`, `delayed`,
`dead_letter`) without changing route paths. `active_scheduler_queue` remains
the sum of scheduled + running + delayed.

---

## Frontend

- Case drawer **Execution**: vertical timeline Scheduled → Sent → Delivered →
  Retry → Captured/Failed with timestamps. Execute / Schedule / Replay still
  call the existing APIs.
- Recovery queue: action chips (Scheduled, Link Sent, Retrying, Delivered, Failed).
- Dashboard: Scheduled Actions Today, Payment Links Sent, Successful Retries,
  Failed Deliveries, plus Scheduler Queue (scheduled, running, delayed,
  dead-letter).
- Audit Timeline: **Webhook replay** (blue) and **Duplicate prevented** (purple)
  badges on feed cards and the inspector.

When live APIs are down, FitLife seed-42 chips and KPIs still render.
