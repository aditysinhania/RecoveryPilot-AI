# Razorpay Webhooks — Phase 10A

Live inbound Razorpay webhooks. Signature verification lives in
`integrations/razorpay/`. Inbox persistence and orchestrator dispatch live in
`services/razorpay_webhooks/`. FastAPI routers stay thin.

Planner, diagnosis, policy, and executor engines are unchanged. Simulator
datasets and existing database relationships / PostgreSQL enums are unchanged.

---

## What it does

1. Accept `POST /api/v1/webhooks/razorpay` with the **raw** JSON body.
2. Verify `X-Razorpay-Signature` as HMAC-SHA256 hex of that body using
   `RAZORPAY_WEBHOOK_SECRET`. Invalid or missing signatures return **401** and
   are **not** stored.
3. Persist every verified delivery in `webhook_events` keyed by unique
   `razorpay_event_id`.
4. Short-circuit duplicate deliveries (idempotent). A replay increments the
   ingest envelope and appends a `WEBHOOK_REPLAY` audit event.
5. Dispatch supported events through `ActionOrchestrator.apply_provider_webhook`.
   Recovery status is updated only on that orchestrator path.
6. Map the event onto an existing recovery case via `notes.recovery_case_id`,
   `payments.razorpay_payment_id` / `razorpay_order_id`, or the Razorpay
   resource id stored on `recovery_actions`.

The webhook path never calls Razorpay HTTP APIs and never re-runs planner,
policy, or diagnosis.

---

## Signature

Razorpay signs the exact request bytes. The API must HMAC the raw body
(`await request.body()`), not a re-serialized dict.

| Item | Value |
| --- | --- |
| Header | `X-Razorpay-Signature` |
| Algorithm | HMAC-SHA256, lowercase hex |
| Secret | `RAZORPAY_WEBHOOK_SECRET` |
| Invalid | HTTP 401, `code=invalid_webhook_signature` |

Empty secret or missing header always fails. Compare is timing-safe and
rejects length-mismatched signatures without raising.

---

## Inbox (`webhook_events`)

Existing table. No new columns and no foreign keys.

| Field | Role |
| --- | --- |
| `razorpay_event_id` | Unique provider event id (idempotency) |
| `event_type` | Razorpay `event` string |
| `payload` | Raw JSON plus local `_rp_ingest` envelope |
| `signature_verified` | Always `true` for stored rows (invalid never persist) |
| `processed_at` | Set after dispatch or after ignoring an unknown type |
| `created_at` | First-seen timestamp (received_at) |

`received_at` is also copied into `payload._rp_ingest.received_at`. Replays
increment `_rp_ingest.replay_count` and set `last_replay_at`. Dispatch failures
set `_rp_ingest.failed` and leave `processed_at` null so Razorpay can retry
without losing the inbox row.

---

## Supported events

| Event | Orchestrator effect | Recovery status |
| --- | --- | --- |
| `payment.captured` | SUCCESS / `PAYMENT_CAPTURED` | `RECOVERED` |
| `payment_link.paid` | SUCCESS / `PAYMENT_CAPTURED` | `RECOVERED` |
| `subscription.charged` | SUCCESS / `PAYMENT_CAPTURED` | `RECOVERED` |
| `subscription.cancelled` | CANCELLED / `RECOVERY_STOPPED` | `STOPPED` |
| `subscription.paused` | CANCELLED / `RECOVERY_STOPPED` | `STOPPED` |
| `payment.failed` | FAILED / `ACTION_EXECUTED` | `WAITING_RETRY` |
| `payment.authorized` | SENT / `ACTION_EXECUTED` | `WAITING_RETRY` |

Unknown event types are stored, marked processed, and **not** dispatched.

---

## Idempotency and replay

A second POST with the same `id` (`razorpay_event_id`):

1. Does not insert a second `webhook_events` row.
2. Increments `_rp_ingest.replay_count`.
3. Does not re-apply recovery status.
4. Appends `audit_logs` with `event_type=ACTION_EXECUTED` and payload flags
   `display_type=WEBHOOK_REPLAY`, `replay`, `webhook_replay`, `duplicate`
   (existing `AuditEventType` enum is not extended).
5. Stamps `request_id` and `correlation_id` on that audit payload.

`AuditEventType` has no `WEBHOOK_REPLAY` value. The frontend already treats
`details.replay || details.webhook_replay` as a replay badge.

---

## Case mapping

Resolution order:

1. `notes.recovery_case_id` on payment, payment_link, subscription, or order
   (must exist as a `recovery_cases` row when a DB session is present).
2. `payments.razorpay_payment_id`
3. `payments.razorpay_order_id`
4. `recovery_actions.razorpay_payment_link` contains the resource id
5. `recovery_actions.action_metadata.razorpay_resource_id`

Unmapped supported events are still stored and marked processed. They do not
create cases.

---

## HTTP

```
POST /api/v1/webhooks/razorpay
GET  /api/v1/webhooks/summary
```

`GET /webhooks/summary` returns `{ received, processed, replayed, failed }`.

- `received` — distinct inbox rows
- `processed` — rows with `processed_at` set
- `replayed` — rows with `_rp_ingest.replay_count > 0`
- `failed` — rows with `_rp_ingest.failed`

Verified ingest returns HTTP 200 even when dispatch fails, so Razorpay does
not infinite-retry a payload we already stored. Invalid signatures are 401.

Audit trail entries include `request_id` and `correlation_id` (headers
`X-Request-ID` / `X-Correlation-ID`).

---

## Layout

```
integrations/razorpay/webhook_signature.py   HMAC verify
services/razorpay_webhooks/                  inbox, mapping, dispatch
apps/backend/app/api/v1/webhooks.py          FastAPI routes
apps/backend/app/services/webhook_service.py HTTP adapter
```

Configure `RAZORPAY_WEBHOOK_SECRET` in `.env` (see `.env.example`). Placeholder
values are for local/CI only.
