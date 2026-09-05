# Data dictionary — synthetic FitLife ecosystem

Field-level reference for every CSV and JSON artefact under `simulator/output/`.
Amounts are integer **paise**. Timestamps are ISO-8601 with `Asia/Kolkata` offset
unless noted. UUIDs are UUID5 (deterministic for a given seed).

Existing CSV **column sets are frozen**. New generator features write *additional*
JSON files (`communication_costs.json`, `customer_behaviour.json`,
`festival_calendar.json`) and do not add columns to the tables below.

Related: [SYNTHETIC_DATASET.md](./SYNTHETIC_DATASET.md).

---

## `customers.csv`

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Customer primary key. |
| `merchant_id` | UUID | Owning merchant (FitLife Gym). |
| `full_name` | string | Indian given + family name. |
| `email` | string | `{firstname}.{lastname}.{index}@gmail.com`. |
| `phone` | string | `+91` Bangalore-style mobile. |
| `customer_segment` | enum | `HIGH_VALUE` `LOYAL` `ACTIVE` `NEW` `AT_RISK` `CHURN_RISK`. |
| `preferred_payment_method` | enum | `UPI` `CARD` `NETBANKING` `WALLET`. |
| `preferred_language` | string | `en` `hi` `kn` `hinglish`. |
| `consent_status` | enum | `GRANTED` `PENDING` `WITHDRAWN`. |
| `consent_whatsapp` | bool | WhatsApp outreach allowed. |
| `consent_sms` | bool | SMS outreach allowed. |
| `consent_voice` | bool | Voice outreach allowed. |
| `salary_dependent` | bool | NSF-before-payday / recover-after-credit overlay. |
| `created_at` | datetime | Membership start (may predate the 90-day window). |
| `updated_at` | datetime | Snapshot time (`as_of`). |

---

## `subscriptions.csv`

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Subscription primary key. |
| `customer_id` | UUID | Payer. |
| `merchant_id` | UUID | Merchant. |
| `subscription_name` | string | `{plan_brand} {plan_name}` (default `FitLife Starter` …). |
| `plan_name` | string | `Starter` `Pro` `Elite` `Premium`. Generator-only; not an ORM column. |
| `billing_amount` | int | Plan price in paise. |
| `billing_frequency` | enum | `MONTHLY` `QUARTERLY` `YEARLY`. |
| `billing_day` | int | 1–28. Generator-only. |
| `next_billing_date` | date | Next mandate charge. |
| `mandate_status` | enum | `PENDING` `ACTIVE` `PAUSED` `REVOKED` `EXPIRED`. |
| `subscription_status` | enum | `ACTIVE` `PAUSED` `PAST_DUE` `CANCELLED` `COMPLETED`. |
| `started_at` | datetime | First billing relationship. Generator-only. |
| `renewal_count` | int | Approximate months since start. Generator-only. |
| `created_at` | datetime | Row creation. |
| `updated_at` | datetime | Snapshot time. |

---

## `payments.csv`

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Payment attempt primary key. |
| `merchant_id` | UUID | Merchant. |
| `customer_id` | UUID | Payer. |
| `subscription_id` | UUID | Plan being charged. |
| `razorpay_order_id` | string | `order_…` public id. |
| `razorpay_payment_id` | string | `pay_…` public id. |
| `idempotency_key` | string | `{prefix}:{subscription_id}:{due}:1` (or `:retry` / `:topup`). |
| `payment_status` | enum | `CAPTURED` or `FAILED` on original attempts. Retries are `CAPTURED`. |
| `failure_reason` | enum\|empty | Set only on failures. See failure table in SYNTHETIC_DATASET. |
| `payment_method` | enum | Instrument used. |
| `amount` | int | Paise; matches `subscriptions.billing_amount`. |
| `currency` | string | Always `INR`. |
| `attempt_number` | int | `1` original invoice; `2` recovery retry. |
| `payment_due_date` | date | Mandate due date. |
| `payment_time` | datetime | Attempt timestamp. Generator-only. |
| `paid_at` | datetime\|empty | Capture time; empty when failed. |
| `created_at` | datetime | Ledger insert (inside the 90-day window). |
| `updated_at` | datetime | Last status change. |
| `plan_name` | string | Denormalised plan. Generator-only. |
| `salary_dependent` | bool | Copied from customer. Generator-only. |
| `segment` | enum | Copied from customer. Generator-only. |
| `is_original_failure` | bool | True iff this row opened a recovery case. Generator-only. |

---

## `recovery_cases.csv`

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Case primary key (1:1 with original failed payment). |
| `payment_id` | UUID | Failed payment. |
| `customer_id` | UUID | Payer. |
| `merchant_id` | UUID | Merchant. |
| `recovery_status` | enum | `DIAGNOSED` `WAITING_RETRY` `WAITING_PROMISE` `RECOVERED` `STOPPED` `ESCALATED` `CLOSED`. |
| `diagnosed_reason` | enum | Same family as `payments.failure_reason`. |
| `diagnosis_model` | string | Default `recoverypilot-rules-v1`. |
| `diagnosis_version` | string | Default `1.0.0`. |
| `ai_confidence` | float | 0–1 heuristic, not an ML score. |
| `priority_score` | float | Queue rank from segment + amount + dispute. |
| `recovery_started_at` | datetime | Diagnosis time. |
| `recovery_completed_at` | datetime\|empty | Terminal time; empty if still waiting. |
| `journey` | string | `A_RETRY` `A_PAYDAY` `A_SWITCH` `B_PROMISE` `C_STOP` `C_ESCALATE` `D_ALREADY_PAID`. Generator-only. |
| `ai_recovered` | bool | AI strategy recovered this case. Generator-only. |
| `ai_suppressed` | bool | Policy stopped / blocked chase. Generator-only. |
| `ai_escalated` | bool | Human escalation. Generator-only. |
| `amount` | int | Paise at risk. Generator-only (not on ORM case). |
| `created_at` | datetime | Case opened. |
| `updated_at` | datetime | Last transition. |

---

## `recovery_actions.csv`

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Action primary key. |
| `recovery_case_id` | UUID | Parent case. |
| `action_type` | enum | `RETRY_PAYMENT` `GENERATE_PAYMENT_LINK` `SWITCH_PAYMENT_METHOD` `WAIT_FOR_PAYDAY` `PROMISE_TO_PAY` `ESCALATE_TO_AGENT` `STOP_RECOVERY` `NO_ACTION`. |
| `scheduled_time` | datetime | When the scheduler intended to run it. |
| `executed_time` | datetime\|empty | Actual run; empty if still `SCHEDULED`. |
| `execution_status` | enum | `SCHEDULED` `SUCCEEDED` `FAILED` `SKIPPED`. |
| `razorpay_payment_link` | string\|empty | Hosted link when a pay-link was issued. |
| `retry_number` | int | 0 for first intervention. |
| `response_code` | string | `OK` or `SKIPPED`. |
| `response_message` | string | Short reason copied from metadata. |
| `action_metadata` | JSON string | `{retry_reason, scheduler_id, payment_link_id?}`. ORM column `metadata`. |
| `created_at` | datetime | Row creation. |

---

## `promises_to_pay.csv`

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Promise primary key. |
| `recovery_case_id` | UUID | Parent case. |
| `promised_amount` | int | Paise the customer committed. |
| `paid_amount` | int | Paise actually collected (0 if open/broken; may be half if partial). Generator-only. |
| `promised_date` | date | Commitment day. |
| `promise_status` | enum | `OPEN` `FULFILLED` `BROKEN`. |
| `fulfilled_at` | datetime\|empty | Capture time if fulfilled. |
| `created_at` | datetime | Promise recorded. |

---

## `audit_logs.csv`

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Audit primary key. |
| `recovery_case_id` | UUID | Case being replayed. |
| `actor_type` | enum | `SYSTEM` `AI_AGENT` `POLICY_ENGINE` `MERCHANT_USER` `CUSTOMER` `SIMULATOR`. |
| `actor_name` | string | Display name (`Diagnosis Agent`, `Policy Engine`, `Razorpay Webhook`, …). |
| `event_type` | enum | `CASE_OPENED` `DIAGNOSIS_COMPLETED` `POLICY_EVALUATED` `ACTION_SCHEDULED` `PAYMENT_CAPTURED` `PROMISE_*` `RECOVERY_STOPPED` `ESCALATED` `CASE_CLOSED` … |
| `event_summary` | string | One-line human replay text. |
| `structured_payload` | JSON string | Machine-readable diagnosis / policy payload. |
| `policy_decision` | enum\|empty | `ALLOW` `BLOCK` `ESCALATE`. |
| `created_at` | datetime | Event time (sequence key). |

---

## `merchant_metrics.csv`

One snapshot row. Schema is frozen — communication ROI lives in
`communication_costs.json`, not here.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Snapshot id. |
| `merchant_id` | UUID | Merchant. |
| `revenue_at_risk` | int | Sum of failed-payment paise. |
| `recovered_revenue` | int | Paise recovered by the AI strategy. |
| `suppressed_revenue` | int | Paise not chased (already-paid, revoked, dispute, …). |
| `recovery_rate` | float | `recovered_revenue / revenue_at_risk`. |
| `escalation_count` | int | Cases sent to a human. |
| `policy_stop_count` | int | Cases with status `STOPPED`. |
| `average_recovery_hours` | float | Mean hours start→complete for recovered cases. Generator-only extra. |
| `updated_at` | datetime | Snapshot time. |

---

## `webhook_events.csv`

Inbox. No domain FK. Duplicate `razorpay_event_id` values are intentional redeliveries.

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Inbox row id (unique even for duplicates). |
| `razorpay_event_id` | string | Provider event id (`evt_…`). Shared across retries. |
| `event_type` | string | `payment.failed` `payment.captured` `payment.authorized` `payment_link.paid` `subscription.charged` `subscription.cancelled`. |
| `payload` | JSON string | Raw Razorpay-shaped body. |
| `signature_verified` | bool | HMAC check result (~97% true). |
| `processed_at` | datetime | When the inbox worker handled it. |
| `created_at` | datetime | Delivery time. |
| `payment_id` | UUID | Generator convenience for validation; not stored on the ORM table. |

---

## `outage_events.json`

Array of rail incidents.

| Field | Type | Description |
| --- | --- | --- |
| `outage_id` | UUID | Incident id. |
| `institution` | string | `SBI` `HDFC` `NPCI` `Axis Bank`. |
| `rail` | string | `UPI` `CARD` `NETBANKING`. |
| `failure_reason` | enum | Forced reason for matching payments. |
| `started_at` | datetime | Inclusive. |
| `ended_at` | datetime | Exclusive end used by `contains`. |
| `summary` | string | Human label. |

---

## `dataset_summary.json`

| Field | Type | Description |
| --- | --- | --- |
| `seed` | int | RNG seed (default 42). |
| `merchant` | string | Display name. |
| `as_of` | datetime | End of observation window. |
| `lookback_days` | int | Default 90. |
| `counts` | object | Row counts per CSV table. |
| `failed_payments` | int | Original failures (= recovery cases). |

---

## `merchant_summary.json`

| Field | Type | Description |
| --- | --- | --- |
| `merchant` | object | Merchant row (`id`, `merchant_name`, `business_category`, `email`, `phone`, `razorpay_account_id`, `timezone`, `created_at`, `updated_at`). |
| `plans` | object | Plan name → paise. |
| `metrics` | object | Same KPI fields as `merchant_metrics.csv`. |
| `city` | string | Default Bangalore. |
| `timezone` | string | `Asia/Kolkata`. |

---

## `simulation_summary.json`

| Field | Type | Description |
| --- | --- | --- |
| `ai` | object | `recovered_revenue`, `revenue_at_risk`, `recovery_rate`, `suppressed_revenue`, `escalation_count`, `policy_stop_count`, `average_recovery_hours`. |
| `baseline` | object | Immediate-retry strategy: `recovered_count`, `recovered_revenue`, `harmful_retries`, `recovery_rate`, `notes`. |
| `lift_recovered_revenue` | int | AI recovered paise minus baseline. |
| `harmful_retries_avoided` | int | Baseline retries on already-paid / dispute / revoked / cancelled. |

---

## `validation_report.json`

| Field | Type | Description |
| --- | --- | --- |
| `ok` | bool | True when `error_count` is 0. |
| `error_count` | int | Number of integrity failures. |
| `errors` | string[] | Up to 50 messages. |
| `counts` | object | Per-CSV row counts. |
| `failed_payments` | int | Original failures. |
| `recovery_cases` | int | Case count. |
| `duplicate_webhook_event_ids` | int | Redeliveries (`n_webhooks − unique evt ids`). |

---

## `communication_costs.json` *(new)*

Does not alter `merchant_metrics.csv`. Unit costs are configurable on
`GeneratorConfig` (`sms_cost_paise` 15, `whatsapp_cost_paise` 80,
`voice_cost_paise` 250).

| Field | Type | Description |
| --- | --- | --- |
| `unit_costs_paise` | object | Per-channel paise. |
| `ai.sms_count` | int | Consent-aware SMS sends from executed actions. |
| `ai.whatsapp_count` | int | WhatsApp utility messages. |
| `ai.voice_count` | int | Voice attempts (escalations). |
| `ai.suppressed_count` | int | Actions skipped for missing consent / no-op types. |
| `ai.*_cost_paise` | int | Count × unit cost. |
| `ai.total_cost_paise` | int | Sum of channel costs. |
| `ai.recovered_revenue_paise` | int | Same as merchant KPI. |
| `ai.net_recovered_paise` | int | Recovered minus comms cost. |
| `ai.recovery_roi` | float | Recovered / comms cost. |
| `baseline.*` | object | One generic SMS per failed payment; no WhatsApp/voice. |
| `roi_lift` | float | AI ratio-ROI minus baseline (baseline can win this: it under-spends). |
| `net_lift_paise` | int | Extra paise recovered after outreach cost (AI minus baseline). |
| `notes` | string | How to read ratio ROI vs net lift. |

Channel mapping (then consent fallback WhatsApp→SMS, Voice→WhatsApp→SMS):

- `RETRY_PAYMENT`, `WAIT_FOR_PAYDAY` → SMS
- `GENERATE_PAYMENT_LINK`, `SWITCH_PAYMENT_METHOD`, `PROMISE_TO_PAY` → WhatsApp
- `ESCALATE_TO_AGENT` → Voice
- `STOP_RECOVERY`, `NO_ACTION` → none

---

## `customer_behaviour.json` *(new)*

90-day stickiness. Default gym generation does **not** re-pick failures
(`enable_behaviour_persistence=False`); streaks are still *observed* on the
ledger. SaaS / EdTech / OTT profiles turn persistence on so the same customers
fail consecutive invoices.

| Field | Type | Description |
| --- | --- | --- |
| `customers` | int | Profile count. |
| `customers_with_fail_streak_2plus` | int | At least two consecutive failed invoices. |
| `customers_with_capture_streak_3plus` | int | At least three consecutive captures. |
| `persistence_enabled_at_generation` | bool | Whether failure clustering ran. |
| `rows[]` | array | Per-customer profile. |
| `rows[].customer_id` | UUID | Customer. |
| `rows[].segment` | enum | Persona. |
| `rows[].salary_dependent` | bool | Payday overlay. |
| `rows[].latent_pay_discipline` | float | Sticky 0–1 score hashed from id + segment (no extra RNG). |
| `rows[].invoice_attempts` | int | First-attempt invoices in the window. |
| `rows[].failed_invoices` | int | Original failures. |
| `rows[].captured_invoices` | int | First-attempt captures. |
| `rows[].max_fail_streak` | int | Longest consecutive fail run. |
| `rows[].max_capture_streak` | int | Longest consecutive capture run. |
| `rows[].observed_reliability` | float | `1 − failed/attempts`. |
| `rows[].sticky_behaviour` | bool | Fail streak ≥ 2 or capture streak ≥ 3. |

---

## `festival_calendar.json` *(new)*

Optional bias. Default gym run sets `enabled: false`, so payment CSVs do not
change. EdTech and OTT profiles set `enable_festival_calendar=True`.

| Field | Type | Description |
| --- | --- | --- |
| `enabled` | bool | Whether festival weights ran during failure diagnosis. |
| `timezone` | string | `Asia/Kolkata`. |
| `festivals[]` | array | Static 2026 calendar. |
| `festivals[].date` | date | Calendar day. |
| `festivals[].name` | string | Bakrid, Muharram, Rath Yatra, Guru Purnima, Independence Day, Onam, Raksha Bandhan, Janmashtami. |
| `festivals[].effect` | string | Why the rail moves (UPI congestion, bank holiday, …). |
| `festivals[].in_observation_window` | bool | Overlaps the 90-day window. |
| `festivals[].applied` | bool | `enabled AND in_observation_window`. |

When applied, `_pick_failure_reason` multiplies `UPI_FAILURE` ×1.65,
`BANK_TIMEOUT` ×1.40, `INSUFFICIENT_FUNDS` ×1.15. No extra RNG.

---

## Merchant templates (`merchant_profiles.py`)

| Key | Merchant | Notes |
| --- | --- | --- |
| `gym` | FitLife Gym | Default. Bit-identical to original FitLife CSVs. |
| `saas` | CloudLedger | Card-heavy B2B, persistence on. |
| `edtech` | LearnHub Academy | Festival calendar + persistence. |
| `ott` | StreamBox | Wallet mix, higher churn, festivals + persistence. |

```python
from simulator.merchant_profiles import config_from_profile
from simulator.dataset_generator import generate_and_write

generate_and_write(config_from_profile("saas"))
```

Plan names stay `Starter` / `Pro` / `Elite` / `Premium` so CSV enums and
downstream modules keep working; only paise and brand prefix change.
