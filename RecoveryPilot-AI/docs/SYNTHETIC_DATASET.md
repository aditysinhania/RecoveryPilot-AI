# Synthetic dataset — FitLife Gym

Deterministic generator for RecoveryPilot AI (Razorpay Hackathon Track 03).
It does **not** sample random fake rows. It simulates a Bangalore recurring-gym
merchant the way an internal Razorpay analytics pipeline would: personas,
salary cycles, rail outages, bounded recovery journeys, webhook redeliveries,
and a baseline-vs-AI comparison.

## Dataset architecture

```
FitLife Gym (merchant)
  └── customers (personas + consent + salary overlay)
        └── subscriptions (plans, mandate, renewals)
              └── payments (90-day ledger, attempts, Razorpay ids)
                    └── recovery_cases (1:1 with original FAILED payments)
                          ├── recovery_actions
                          ├── promises_to_pay
                          └── audit_logs (replay timeline)
webhook_events  ← inbox, not FK-bound, may duplicate razorpay_event_id
outage_events   ← SBI / HDFC / NPCI / Axis windows
merchant_metrics ← AI strategy snapshot
communication_costs.json ← SMS / WhatsApp / Voice spend + recovery ROI
customer_behaviour.json ← 90-day payment stickiness
festival_calendar.json ← optional Indian festival bias (off for FitLife)
```

Amounts are **integer paise**. Timezone is **Asia/Kolkata**. The observation
window is 90 days ending `2026-09-02 18:00 IST` (configurable).

## Generation pipeline

Modules live under `simulator/src/simulator/` (uv/src layout):

| Module | Role |
| --- | --- |
| `config.py` | Seed, volumes, FitLife plans, weights, festival / persistence flags |
| `merchant_profiles.py` | Gym / SaaS / EdTech / OTT templates (`config_from_profile`) |
| `distributions.py` | Weighted draws, personas, salary cycle, outages, festivals |
| `event_generator.py` | Customers → subs → payments → journeys → metrics |
| `webhook_generator.py` | Razorpay inbox + intentional duplicates |
| `dataset_generator.py` | CSV/JSON writers + `validation_report.json` |
| `seed_database.py` | Optional Postgres hydrate from CSV |

Run from the RecoveryPilot-AI root:

```powershell
$env:PYTHONPATH = "simulator\src;shared\src"
python -m simulator
```

Same seed (`42` by default) always yields the same UUIDs, Razorpay-like ids,
and CSV bytes (UUID5 + `random.Random(seed)` + NumPy Generator + Faker seed).

## Merchant context

- **Name:** FitLife Gym
- **Category:** Fitness & Wellness (recurring subscription)
- **City:** Bangalore, India
- **Timezone:** Asia/Kolkata
- **Plans (paise):** Starter ₹499 (`49900`), Pro ₹999 (`99900`), Elite ₹1499 (`149900`), Premium ₹2499 (`249900`)
- Plan mix is persona-shifted: HIGH_VALUE is Elite/Premium-heavy; NEW is Starter-heavy.

## Target volumes (`config.py`)

| Entity | Default |
| --- | ---: |
| Customers | 1200 |
| Subscriptions | 1800 (primary + renewal/upgrade history) |
| Payment attempts | 5000 |
| Failed payments / recovery cases | 750 |
| Recovery actions | 1000 |
| Promises-to-pay | 250 |
| Audit events | floor 1000; full replay trail is emitted (~3.5k) |
| Webhook events | 500 (~14% duplicate deliveries) |

`n_audit_events` is a **floor**. The generator writes a complete replayable
timeline (several events per case) so Audit Replay can step through every
journey without gaps.

## Persona definitions

| Segment | Weight | Behaviour |
| --- | ---: | --- |
| HIGH_VALUE | 10% | Premium plans, cards more common, recovers after first smart retry / reminder |
| LOYAL | 30% | Pro/Elite, stable mandates, high promise fulfilment |
| ACTIVE | 25% | India-typical UPI mix, moderate salary overlay |
| NEW | 15% | Starter, pending mandates, card-auth / first-mandate failures |
| AT_RISK | 12% | Strongly salary-dependent; NSF before payday, recover 1st–5th |
| CHURN_RISK | 8% | Misses retries, revoked mandates, broken promises → escalate |

**Salary-dependent overlay** (not a segment): AT_RISK ~78%, ACTIVE ~28%, CHURN_RISK ~40%, HIGH_VALUE ~5%. Recovery for these rows is gated on calendar day, not a coin flip.

Languages: `en` 40%, `hi` 25%, `kn` 20%, `hinglish` 15%. Consent flags: WhatsApp / SMS / Voice, rolled into `consent_status`.

## Subscription behaviour

- Frequencies: Monthly 90%, Quarterly 8%, Yearly 2%.
- Billing day uniform in 1–28.
- Mandates: ACTIVE / PAUSED / REVOKED / EXPIRED / PENDING (NEW).
- Extra completed/cancelled rows provide **renewal history** (`renewal_count`).

## Payment behaviour

Last 90 days. Methods resemble Indian digital payments:

| Method | Weight |
| --- | ---: |
| UPI | 62% |
| Card | 22% |
| Net banking | 10% |
| Wallet | 6% |

HIGH_VALUE is card-heavier; NEW is UPI-heavier.

Each row has `attempt_number`, `payment_due_date`, `payment_time`, `paid_at`,
`payment_method`, `amount`, `currency`, `status`, `failure_reason`,
`razorpay_order_id`, `razorpay_payment_id`, `idempotency_key`.

Original failures stay `FAILED`. A successful recovery appends a **second
attempt** (`attempt_number=2`, `CAPTURED`).

## Failure reason distribution

Configurable in `GeneratorConfig.failure_weights`:

| Reason | Weight |
| --- | ---: |
| INSUFFICIENT_FUNDS | 45% |
| UPI_FAILURE | 18% |
| BANK_TIMEOUT | 12% |
| CARD_EXPIRED | 9% |
| MANDATE_REVOKED | 6% |
| CUSTOMER_CANCELLED | 4% |
| ALREADY_PAID | 3% |
| DISPUTE | 2% |
| UNKNOWN | 1% |

Biases: late-month NSF multiplier, UPI/card method tilt, weekend timeout tilt.
Payments that land inside a matching rail outage **must** fail with that
outage's timeout reason.

## Salary-cycle modelling

Indian payroll pattern, evaluated in IST:

- **25th–31st:** NSF likelihood ×1.8 (pre-payday squeeze).
- **1st–5th:** NSF ×0.45; payday retry success ~0.92.
- **6th–10th:** payday retry ~0.55; otherwise ~0.18.
- Weekends inflate UPI/bank timeouts.
- `WAIT_FOR_PAYDAY` journeys schedule the retry onto the next 1st–5th window.
- Recovery is **rule-based** from persona + reason + calendar day.

## Outage modelling

Six windows in `outage_events.json` (seed-stable):

- SBI CBS maintenance → `BANK_TIMEOUT`
- HDFC acquiring latency → `BANK_TIMEOUT`
- NPCI UPI switch timeout → `UPI_FAILURE`
- Axis Bank downtime → `BANK_TIMEOUT`
- NPCI regional degradation → `UPI_FAILURE`
- SBI UPI collect errors → `UPI_FAILURE`

A payment whose method maps to the outage rail and whose timestamp is inside
the window is forced to that failure reason. Smart retry is scheduled **after**
`ended_at`.

## Recovery journeys

Every original `FAILED` payment gets exactly one case.

| Journey | Trigger | Outcome |
| --- | --- | --- |
| A retry | UPI/bank timeout, HIGH_VALUE | Diagnosed → retry scheduled → recovered or waiting |
| A payday | NSF + salary-dependent | Wait for payday → retry after credit |
| A switch | CARD_EXPIRED | Switch method / payment link |
| B promise | Churn / some NSF | Promise recorded → fulfilled, broken+escalated, or open |
| C stop | Mandate revoked / cancelled | Policy BLOCK, recovery stopped |
| C escalate | Dispute | Policy ESCALATE, human only |
| D already paid | ALREADY_PAID | NO_ACTION, suppressed |

Not every case recovers. Terminal states: Recovered, Stopped, Escalated,
Waiting Retry, Waiting Promise, Closed.

Diagnosis uses `recoverypilot-rules-v1` / `1.0.0` with reason-specific
confidence (not an ML model).

## Recovery actions

Types: `RETRY_PAYMENT`, `GENERATE_PAYMENT_LINK`, `SWITCH_PAYMENT_METHOD`,
`WAIT_FOR_PAYDAY`, `PROMISE_TO_PAY`, `ESCALATE_TO_AGENT`, `STOP_RECOVERY`,
`NO_ACTION`.

Each row has `scheduled_time`, `executed_time`, `execution_status`,
`retry_number`, and `action_metadata` JSON (`payment_link_id`, `scheduler_id`,
`retry_reason`).

## Promises-to-pay

~250 rows. Statuses: OPEN / FULFILLED / BROKEN. A subset of fulfilled promises
are **partial** (`paid_amount` < `promised_amount`). Delay is 0–4 days after
the promised date.

## Webhook modelling

Inbox events (no domain FK):

- `payment.failed`, `payment.authorized`, `payment.captured`
- `payment_link.paid`, `subscription.charged`, `subscription.cancelled`

~14% are **redeliveries** sharing `razorpay_event_id` with a later
`processed_at`. `signature_verified` is true on ~97%. `payload` is the raw JSON
body. `seed_database.py` de-duplicates on `razorpay_event_id` because the
Postgres column is unique.

## Audit timeline

Actors: Diagnosis Agent (`AI_AGENT`), Policy Engine, Recovery Executor /
Scheduler / Razorpay Webhook (`SYSTEM`), Merchant (`MERCHANT_USER`), Customer.

Sequence follows the journey: CASE_OPENED → DIAGNOSIS_COMPLETED →
POLICY_EVALUATED → ACTION_* → PROMISE_* / PAYMENT_CAPTURED → CASE_CLOSED.

`structured_payload` is JSON; `policy_decision` is ALLOW / BLOCK / ESCALATE.

## Merchant metrics (AI strategy)

Computed after the simulation:

- Revenue at risk, recovered revenue, recovery rate
- Suppressed revenue (already-paid, revoked, dispute — money we refused to chase)
- Escalations, policy stops, average recovery hours

## Baseline vs AI

Baseline = immediate retry, generic reminder, **no diagnosis, no stopping
rules**. It "recovers" only timeout-like failures and **harmfully retries**
already-paid / dispute / revoked / cancelled.

`simulation_summary.json` stores AI KPIs, baseline KPIs, recovered-revenue lift,
and `harmful_retries_avoided`.

## CSV schemas

Output directory: `simulator/output/` (created on run).

### `customers.csv`

`id, merchant_id, full_name, email, phone, customer_segment, preferred_payment_method, preferred_language, consent_status, consent_whatsapp, consent_sms, consent_voice, salary_dependent, created_at, updated_at`

### `subscriptions.csv`

`id, customer_id, merchant_id, subscription_name, plan_name, billing_amount, billing_frequency, billing_day, next_billing_date, mandate_status, subscription_status, started_at, renewal_count, created_at, updated_at`

### `payments.csv`

`id, merchant_id, customer_id, subscription_id, razorpay_order_id, razorpay_payment_id, idempotency_key, payment_status, failure_reason, payment_method, amount, currency, attempt_number, payment_due_date, payment_time, paid_at, created_at, updated_at, plan_name, salary_dependent, segment, is_original_failure`

### `recovery_cases.csv`

`id, payment_id, customer_id, merchant_id, recovery_status, diagnosed_reason, diagnosis_model, diagnosis_version, ai_confidence, priority_score, recovery_started_at, recovery_completed_at, journey, ai_recovered, ai_suppressed, ai_escalated, amount, created_at, updated_at`

### `recovery_actions.csv`

`id, recovery_case_id, action_type, scheduled_time, executed_time, execution_status, razorpay_payment_link, retry_number, response_code, response_message, action_metadata, created_at`

### `promises_to_pay.csv`

`id, recovery_case_id, promised_amount, paid_amount, promised_date, promise_status, fulfilled_at, created_at`

### `audit_logs.csv`

`id, recovery_case_id, actor_type, actor_name, event_type, event_summary, structured_payload, policy_decision, created_at`

### `merchant_metrics.csv`

`id, merchant_id, revenue_at_risk, recovered_revenue, suppressed_revenue, recovery_rate, escalation_count, policy_stop_count, average_recovery_hours, updated_at`

### `webhook_events.csv`

`id, razorpay_event_id, event_type, payload, signature_verified, processed_at, created_at, payment_id`

`payment_id` is a generator convenience for validation; the ORM table has no FK.

## JSON summaries

- `dataset_summary.json` — seed, as-of, row counts
- `merchant_summary.json` — FitLife profile + plans + AI metrics
- `simulation_summary.json` — AI vs baseline
- `outage_events.json` — rail incidents
- `validation_report.json` — quality gates
- `communication_costs.json` — SMS / WhatsApp / Voice cost and recovery ROI
- `customer_behaviour.json` — 90-day payment stickiness
- `festival_calendar.json` — Indian festival dates (off by default)

Field-level schemas: [DATA_DICTIONARY.md](./DATA_DICTIONARY.md).

## Data quality validation

`validate_dataset()` checks:

- No orphan FKs (customer / subscription / case)
- Every original failed payment has a recovery case
- Every action, promise, and audit belongs to a case
- Payment timestamps sit inside the 90-day window
- Amounts match the subscription plan
- Webhooks reference existing payments

## What this is not

No FastAPI routes, no LLM inference, no dashboard code. Diagnosis confidence
is a calibrated heuristic so the queue and audit replay have realistic scores.
