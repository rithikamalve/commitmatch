# CommitMatch

AI-powered blood donor matching platform built for the **Blood Warriors NGO** hackathon. CommitMatch connects thalassemia patients with the right blood donors at the right time — using commitment scoring, donation rhythm prediction, and WhatsApp-based outreach to turn "maybe" donors into confirmed life-savers.

---

## What it does

Thalassemia patients need regular transfusions — often every 2–4 weeks. Finding a willing, available, compatible donor in time is a coordination problem that Blood Warriors coordinators solve manually today. CommitMatch automates it:

1. A coordinator creates a blood request for a patient.
2. The system ranks compatible donors by a **commitment score** — factoring in donation history, predicted donation window, past show-rate, and engagement signals.
3. WhatsApp messages are sent to the top-ranked donor (primary) and a backup (standby).
4. Incoming replies are parsed for sentiment; **amber alerts** fire when a donor's reply hints at hesitation.
5. If the primary hasn't confirmed in 4 hours, the standby is automatically promoted.
6. Every confirmation or no-show feeds a **feedback loop** that improves future rankings.

---

## Architecture

```
Frontend (React + Vite)
    │  REST + WebSocket
    ▼
Backend (FastAPI on AWS Lambda)
    │
    ├── Matching Engine       — ranks donors by commitment score
    ├── Engagement Scorer     — predicts donation rhythm window
    ├── WhatsApp (Twilio)     — sends & receives messages
    ├── AI Summarizer (Claude)— generates case summaries
    └── Feedback Loop         — records outcomes, tunes scores
    │
    ▼
DynamoDB (9 tables)          AWS EventBridge (3 scheduled jobs)
```

**AWS services used:** Lambda · DynamoDB · API Gateway (WebSocket) · EventBridge · S3

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python 3.12, FastAPI |
| Database | AWS DynamoDB |
| Messaging | Twilio WhatsApp API |
| AI | Claude (Anthropic) |
| Infra | AWS Lambda, EventBridge, API Gateway WebSockets |

---

## Key features

- **Commitment scoring** — multi-signal donor ranking (history, rhythm, show-rate, recency)
- **Donation rhythm prediction** — predicts when a donor's next safe window opens
- **WhatsApp outreach** — automated messages with sentiment-aware reply parsing
- **Amber alerts** — real-time UI warning when a donor reply suggests soft-cancellation
- **Standby promotion** — auto-escalates to backup donor after 4-hour primary silence
- **Shortage detection** — alerts on blood group shortages by city cluster, updated every 6 hours
- **Feedback loop** — no-shows and declines are logged and used to retrain donor scores
- **AI case summary** — Claude-generated narrative for each request, shown to coordinators

---

## Data model (DynamoDB tables)

| Table | Purpose |
|---|---|
| `commitmatch_donors` | Donor profiles seeded from CSV |
| `commitmatch_patients` | Thalassemia patients (keyed by bridge ID) |
| `commitmatch_requests` | Blood donation requests |
| `commitmatch_rankings` | Per-request donor rankings with signal breakdown |
| `commitmatch_interactions` | WhatsApp inbound/outbound message log |
| `commitmatch_memory` | Donor long-term memory (show-rate, notes, language) |
| `commitmatch_shortage_alerts` | Active shortage alerts by severity |
| `commitmatch_ws_connections` | Live WebSocket connections for real-time push |
| `commitmatch_failure_log` | No-shows, declines, non-responses for feedback |

---

## Scheduled jobs (EventBridge)

| Job | Schedule | What it does |
|---|---|---|
| `standby-promoter` | Every 30 min | Promotes standby if primary silent for 4 hours |
| `rhythm-nudger` | Daily 03:30 UTC | Nudges donors whose window opens within 7 days |
| `shortage-detector` | Every 6 hours | Detects blood group shortages and pushes alerts |

---

## Getting started

### Prerequisites

- Python 3.12+
- Node 18+
- AWS credentials configured (`ap-south-1` region)
- Twilio account with a WhatsApp-enabled number

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Copy and fill in your env vars
cp .env.example .env

python main.py
# API runs at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# Set VITE_API_URL and VITE_WS_URL

npm run dev
# UI runs at http://localhost:5173
```

### Seed demo data

```bash
python scripts/seed_demo.py
```

---

## Environment variables

**Backend** — set in `.env`:

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | Sending WhatsApp number (`whatsapp:+...`) |
| `DEMO_MODE` | `true` to skip real WhatsApp sends |
| `DEMO_WHATSAPP` | `true` to send WhatsApp even in demo mode |

**Frontend** — set in `.env`:

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend API base URL |
| `VITE_WS_URL` | API Gateway WebSocket URL |

---

## Project structure

```
commitmatch/
├── backend/
│   ├── ai/           — Claude-powered case summarizer
│   ├── engagement/   — Donor rhythm & priority scoring
│   ├── learning/     — Feedback loop (confirmation/failure recording)
│   ├── matching/     — Core donor ranking engine
│   ├── memory/       — Donor long-term memory store
│   ├── messaging/    — Twilio WhatsApp send/receive
│   ├── models/       — Pydantic schemas
│   ├── routers/      — FastAPI route handlers
│   └── websocket/    — Real-time push via API Gateway
├── frontend/
│   └── src/
│       ├── components/ — AmberAlert, ShortageAlert, etc.
│       └── lib/        — WebSocket client
├── infra/
│   ├── dynamodb_tables.json
│   └── eventbridge_rules.json
├── data/
│   └── Dataset.csv   — Donor seed data
└── scripts/
    └── seed_demo.py
```
