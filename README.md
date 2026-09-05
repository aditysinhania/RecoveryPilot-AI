# 🚀 RecoveryPilot AI — AI Revenue Recovery for Razorpay Subscriptions

> **Turn failed subscription payments into recovered revenue with AI-powered, RBI-compliant recovery orchestration.**

RecoveryPilot AI is an end-to-end recovery platform built for subscription businesses using **Razorpay**. Instead of repeatedly retrying failed payments, RecoveryPilot diagnoses *why* a payment failed, evaluates recovery policies, chooses the best recovery strategy, executes it safely in Razorpay Sandbox, and maintains a replayable compliance audit trail.

Built for the **Razorpay AI Hackathon 2026**.

---

## 🌟 What RecoveryPilot Solves

Subscription businesses lose revenue because recurring payments fail due to:

* Insufficient Funds (NSF)
* UPI congestion or downtime
* Revoked mandates
* Expired cards
* Bank/network failures

Most systems repeatedly retry payments, causing poor customer experience and violating recovery best practices.

RecoveryPilot introduces an **AI-first recovery engine** that decides **whether to retry, wait, send a payment link, or stop entirely** based on policy and payment context.

**Result:** Higher recovery rate with compliant recovery decisions.

---

## ✨ Key Features

### 🤖 AI Diagnosis Engine

* Detects payment failure reasons.
* Assigns AI confidence scores.
* Generates structured recovery evidence.
* Versioned diagnosis model (`recoverypilot-rules-v1`).

### 🛡️ RBI-Compliant Policy Engine

* Evaluates recovery eligibility.
* Prevents harmful retries.
* Uses bounded recovery policies.
* Creates replayable policy decisions.

### ⚡ Recovery Planner

Chooses exactly one bounded strategy:

* Retry Payment
* Wait for Payday
* Send Payment Link
* Promise to Pay
* Stop Recovery

Never executes conflicting actions.

### 💳 Razorpay Sandbox Executor

* Executes retries.
* Generates payment links.
* Uses idempotency keys.
* Stores execution history.

### 📜 Replayable Audit Timeline

Every recovery decision is stored with:

* Correlation ID
* Request ID
* Actor
* Policy decision
* Metadata
* Timestamp

Designed for operations and compliance teams.

### 📊 Merchant Cockpit

Real-time dashboard with:

* Recovery Rate
* Revenue Recovered
* At-Risk Revenue
* AI Insights
* Recovery Queue
* Analytics
* Operations Health

### 🧪 AI Recovery Simulator

Compare recovery strategies before going live.

Toggle scenarios like:

* Salary-cycle NSF
* Bank downtime
* Festival congestion
* Promise-to-pay

See projected revenue uplift instantly.

# 🧠 Recovery Pipeline

```text
          Razorpay Webhook
                  │
                  ▼
        Payment Failure Inbox
                  │
                  ▼
       AI Diagnosis Engine
                  │
                  ▼
      RBI Policy Evaluation
                  │
                  ▼
        Recovery Planner
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
     WAIT      RETRY      LINK
        │         │         │
        └─────────┴─────────┘
                  │
                  ▼
     Razorpay Sandbox Executor
                  │
                  ▼
        Audit Timeline + Dashboard
```

---

# 🏗️ Architecture

```text
                    Next.js Frontend
                            │
                            ▼
                  FastAPI Backend (JWT Auth)
                            │
        ┌──────────────┬───────────────┬───────────────┐
        ▼              ▼               ▼
   Diagnosis Engine  Policy Engine   Recovery Planner
        │              │               │
        └──────────────┴───────────────┘
                            │
                     Executor Service
                            │
      Razorpay Sandbox  •  Gemini AI  •  Redis Scheduler
                            │
                            ▼
                      PostgreSQL Database
```

---

# 📁 Project Structure

```text
RecoveryPilot-AI
│
├── apps
│   ├── backend                 # FastAPI API
│   └── frontend                # Next.js App
│
├── database                    # PostgreSQL schema & seeds
├── docker                      # Dockerfiles
├── docs                        # API & architecture docs
├── integrations                # Razorpay + Gemini integrations
├── services                    # Business logic engines
├── shared                      # Shared models & utilities
├── simulator                   # Recovery simulator
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── pyproject.toml
└── README.md
```

---

# ⚙️ Tech Stack

| Layer          | Technology                      |
| -------------- | ------------------------------- |
| Frontend       | Next.js 15, React, Tailwind CSS |
| Backend        | FastAPI, Python 3.12            |
| Authentication | JWT + Refresh Tokens + bcrypt   |
| Database       | PostgreSQL                      |
| Scheduler      | Redis-ready recovery scheduler  |
| AI             | Google Gemini API               |
| Payments       | Razorpay Sandbox APIs           |
| Infrastructure | Docker Compose + Nginx          |
| Monitoring     | Sentry-ready hooks              |

---

# 🔐 Authentication

RecoveryPilot includes complete authentication.

### Endpoints

| Endpoint                    | Purpose                 |
| --------------------------- | ----------------------- |
| `POST /api/v1/auth/signup`  | Create operator account |
| `POST /api/v1/auth/login`   | Login                   |
| `POST /api/v1/auth/refresh` | Refresh JWT             |
| `POST /api/v1/auth/logout`  | Logout                  |
| `GET /api/v1/auth/me`       | Current operator        |

Features:

* Access Token
* Refresh Token
* Password hashing
* Session tracking
* Merchant onboarding state

---

# 🏢 Merchant Onboarding

RecoveryPilot creates isolated merchant workspaces.

### Workspace Types

| Workspace       | Purpose                          |
| --------------- | -------------------------------- |
| Empty           | Fresh merchant workspace         |
| FitLife Seed-42 | Demo dataset with recovery cases |

Onboarding stores:

* Merchant profile
* Razorpay Sandbox keys
* Gemini API key
* Notifications
* Timezone
* Workspace metadata

---

# 📊 Merchant Dashboard

Shows business recovery metrics.

### KPIs

| Metric                    | Demo Value |
| ------------------------- | ---------- |
| Recovery Rate             | **69.3%**  |
| Revenue Recovered         | **₹5.83L** |
| At Risk Revenue           | **₹8.42L** |
| Harmful Retries Prevented | **117**    |
| Webhook Events Processed  | **500+**   |

AI Insights surface:

* NSF still dominates at-risk revenue.
* Wait-for-payday outperforms immediate retry.
* Policy engine prevented harmful retries.

---

# 📋 Recovery Queue

Each recovery case contains:

* Customer Profile
* Subscription Details
* Failed Payment
* AI Diagnosis
* Policy Decision
* Planner Strategy
* Executor Status
* Audit Events

### Supported Statuses

* Diagnosed
* Waiting
* Promise
* Recovered
* Failed
* Stopped

---

# 🤖 AI Diagnosis Engine

Inputs:

* Payment method
* Failure reason
* Subscription history
* Customer segment
* Billing calendar

Outputs:

```json
{
  "diagnosed_reason": "UPI_FAILURE",
  "confidence": 0.7079,
  "priority_score": 0.99,
  "model": "recoverypilot-rules-v1",
  "version": "1.0.0"
}
```

---

# 🛡️ Policy Engine

Policy-first recovery decisions.

### Example

| Failure           | Decision |
| ----------------- | -------- |
| UPI Failure       | Retry    |
| NSF before payday | Wait     |
| Revoked mandate   | Stop     |
| Already paid      | Stop     |
| Promise active    | Wait     |

Every decision is recorded.

---

# ⚡ Recovery Planner

Planner selects one bounded action.

| Strategy        | Description         |
| --------------- | ------------------- |
| Retry Payment   | Safe retry window   |
| Wait For Payday | Salary-cycle aware  |
| Payment Link    | Manual recovery     |
| Promise To Pay  | Customer commitment |
| Stop Recovery   | Policy blocked      |

---

# 💳 Razorpay Sandbox Executor

Executor integrates with Razorpay Sandbox.

Capabilities:

* Retry payments.
* Payment links.
* Idempotent execution.
* Execution history.
* Retry counters.
* Response metadata.

---

# 📜 Audit Timeline

Replayable recovery history.

Example timeline:

| Event               | Actor             |
| ------------------- | ----------------- |
| CASE_OPENED         | Razorpay Webhook  |
| DIAGNOSIS_COMPLETED | Diagnosis Agent   |
| POLICY_EVALUATED    | Policy Engine     |
| PAYMENT_CAPTURED    | Recovery Executor |
| CASE_CLOSED         | Recovery Executor |

Every event includes metadata and correlation IDs.

---

# 📈 Analytics

Recovery analytics include:

* Recovery Funnel
* Failure Mix
* Calendar Recovery Windows
* AI Insights
* Revenue Trends
* Recovery Lift

---

# 🧪 Recovery Simulator

Simulate recovery strategies.

### Scenarios

* Salary-cycle NSF
* Bank downtime
* Festival congestion
* Promise-to-pay

Outputs:

* Recovery uplift
* Additional revenue
* AI recommendation
* Strategy comparison

---

# ⚙️ Operations Dashboard

Live health monitoring.

Checks:

* API Health
* PostgreSQL
* Scheduler Queue
* Webhook Inbox
* Queue Depth
* Recovery Workers

---

# 🔗 REST API Highlights

| Endpoint                            | Description        |
| ----------------------------------- | ------------------ |
| `/api/v1/recovery/summary`          | Dashboard KPIs     |
| `/api/v1/recovery/queue`            | Recovery queue     |
| `/api/v1/recovery/cases/{id}`       | Recovery drawer    |
| `/api/v1/recovery/cases/{id}/audit` | Audit timeline     |
| `/api/v1/actions/{id}/status`       | Executor history   |
| `/api/v1/onboarding`                | Merchant workspace |
| `/api/v1/me/merchants`              | Merchant profile   |

Interactive docs available at:

```text
http://localhost:8000/docs
```

---

# 🐳 Running Locally

## Clone

```bash
git clone https://github.com/<your-username>/RecoveryPilot-AI.git
cd RecoveryPilot-AI
```

## Environment

```bash
cp .env.example .env
```

Fill:

```env
DATABASE_URL=...
JWT_SECRET=...
JWT_REFRESH_SECRET=...
GOOGLE_API_KEY=...
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

## Docker

```bash
docker compose up --build
```

### Services

| Service    | URL                        |
| ---------- | -------------------------- |
| Frontend   | http://localhost:8080      |
| Backend    | http://localhost:8000      |
| API Docs   | http://localhost:8000/docs |
| PostgreSQL | localhost:5432             |

---

# 🧪 Demo Dataset

RecoveryPilot ships with **FitLife Seed-42**.

Includes:

* 500+ webhook events.
* Failed subscription payments.
* Recovery cases.
* Audit timeline.
* Analytics.
* Simulator scenarios.

Import from **Recovery Queue → Import Demo Dataset**.

---

# 🧪 Testing

### Health

```bash
curl http://localhost:8000/health
```

### Merchant

```bash
curl http://localhost:8000/api/v1/me/merchants
```

### Recovery Case

```bash
curl http://localhost:8000/api/v1/recovery/cases/<case_id>
```

### Audit Timeline

```bash
curl http://localhost:8000/api/v1/recovery/cases/<case_id>/audit
```

---

# 🔒 Security & Compliance

RecoveryPilot is designed with operational safety in mind.

* JWT authentication.
* Refresh token rotation.
* bcrypt password hashing.
* Idempotent recovery execution.
* Correlation IDs for every request.
* Replayable audit trail.
* Integer paise accounting (no floating-point money).
* Razorpay Sandbox only during demo.

---

# 📌 Roadmap

### ✅ Completed (v1.0)

* Authentication
* Merchant onboarding
* Recovery dashboard
* AI diagnosis engine
* Policy engine
* Recovery planner
* Razorpay Sandbox executor
* Audit timeline
* Analytics
* Simulator
* Operations dashboard
* Docker deployment

### 🚀 Future Work

* Live Razorpay production integration.
* Redis-backed scheduler workers.
* LLM-powered recovery message generation.
* WhatsApp/SMS recovery journeys.
* Multi-tenant merchant organizations.
* Explainable AI policy recommendations.

---

# 👨‍💻 Team

**Adity Sinha**

Engineering AI & Data Science Student

RecoveryPilot AI — Razorpay AI Hackathon 2026

---

# 📄 License

Built for educational and hackathon demonstration purposes.

Razorpay payment execution uses **Sandbox** credentials only.

---

## ⭐ RecoveryPilot AI

**AI-powered revenue recovery for Razorpay subscriptions.**

*Diagnose. Decide. Recover. Audit.*
