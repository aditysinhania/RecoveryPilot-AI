# Demo Experience

Frontend-only SaaS polish for judges and merchants. Diagnosis, policy, planner, executor, Razorpay capture, simulator datasets, and HTTP schemas are unchanged.

## Demo workspace

`/demo` is public. It does not require JWT.

- Landing **Try Live Demo** opens RecoveryPilot on the FitLife seed-42 catalog.
- A top banner reads: `Demo Workspace — No real Razorpay calls. Powered by simulator seed-42.`
- Sidebar, navbar, and the workspace switcher show a purple **DEMO** badge.
- Dashboard, queue, analytics, audit, simulator, operations, and settings reuse the existing ops chrome under `/demo/...`.
- Execute and Schedule stay disabled. The UI never calls live Razorpay from demo.
- Live merchant APIs are skipped; charts and tables bind to the seed-42 snapshot already used when APIs are down.

Exit via **Exit demo** in the navbar (guests) or navigate home.

## Guided tour

First visit to `/demo` or `/dashboard` launches a spotlight walkthrough:

1. Dashboard KPIs
2. AI Insights
3. Recovery Queue
4. Analytics
5. Audit Timeline
6. Simulator Lab

Controls: Next, Previous, Skip Tour, Finish, Escape. Completion is stored as `localStorage.rp_product_tour_v1 = done`.

## Onboarding

Signup still redirects to `/onboarding`. Four UI steps:

1. **Merchant Profile** — name, business type, company size, monthly volume. Size and volume stay in `localStorage` (`rp_onboarding_profile`). Name and type use the existing onboarding APIs.
2. **Razorpay Sandbox** — key id, secret, format checks, Test Connection (format only; no Razorpay HTTP call).
3. **AI Configuration** — optional Gemini key, AI explanations toggle (local), notification checkboxes via existing account APIs.
4. **Workspace Choice** — Load Demo Workspace (FitLife) or Start Empty Workspace. Finish goes to `/dashboard`.

Progress indicator and animated step transitions are frontend-only.

## Empty workspace

When `workspace_kind === empty` and that merchant is selected:

- Dashboard, queue, analytics, and audit show an illustrated empty state instead of blank charts.
- Cards: Connect Razorpay Sandbox, Import Demo Dataset (switches the workspace picker to FitLife), Read Documentation, Open Simulator.

Switching to FitLife in the workspace switcher loads seed-42 without changing the backend tenant.

## Workspace switching

The navbar dropdown shows avatar initials, merchant name, industry badge, and **DEMO** for the FitLife simulator merchant (and the entire `/demo` session). Selection animates the label.

## Toasts

Bottom-right stack (success / warning / error):

- Success: payment link generated, scheduler created, workspace saved.
- Warning: live API unavailable, running simulator data.
- Error: failed connection, invalid Razorpay keys.

## Demo video

Landing **Watch 2-minute Demo** opens a blurred-backdrop modal with a placeholder player and chapters: AI Diagnosis, Planner, Dashboard, Simulator. Escape closes it.
