🛡️ RTO Shield & Recovery Agent

> An AI-powered multi-agent system that detects high-risk COD orders before they ship and manages post-return recovery — turning RTO losses into recovered revenue.

**Inspired by [Razorpay's RTO Shield](https://razorpay.com/rto/) and their Agentic AI vision with Agent Studio.**



---

## 📑 Table of Contents

- [The Problem](#-the-problem)
- [The Solution](#-the-solution-two-ai-agents-working-in-tandem)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [React Frontend](#-react-frontend)
- [API Reference](#-api-reference)
- [Environment Variables](#-environment-variables)
- [Contributing](#-contributing)

---

## 🎯 The Problem

Cash on Delivery accounts for **~60% of Indian e-commerce**, but carries a devastating side effect: **Return to Origin (RTO)**. When customers refuse delivery or addresses are incorrect, merchants face:

| Pain Point | Impact |
|---|---|
| Forward + reverse shipping | ₹100–300 wasted per order |
| High-risk categories | 25–40% RTO rates |
| Manual risk assessment | Slow, error-prone, unscalable |
| Products stuck in transit | Lost revenue & inventory limbo |

> For a merchant processing **10,000 COD orders/month** with a **30% RTO rate**, that's **₹4.5–9 Lakhs/month** in pure shipping losses.

---

## 🤖 The Solution: Two AI Agents Working in Tandem

### Agent 1 — 🛡️ The Shield Agent (Pre-Dispatch)

Analyzes every COD order **before** it ships using:

- **Behavioral Analysis** — Customer history, past RTO rate, account age, verification status
- **Address Intelligence** — Pincode-city validation, vague address detection, geocoding
- **Risk Scoring Engine** — Weighted composite score across 5 risk dimensions
- **Autonomous Actions** — Approve / Request verification / Recommend cancellation

### Agent 2 — 🔄 The Recovery Agent (Post-Return)

Activates after RTO to salvage revenue:

- **Empathetic Re-engagement** — Personalized WhatsApp messages (not complaint-style!)
- **Dynamic Incentives** — LLM-generated discount codes calibrated to order value
- **Payment Link Generation** — Razorpay payment links for frictionless re-ordering
- **Inventory Management** — Tracks returned items through the inspection pipeline

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│           React Frontend  (port 3000)               │
│     Dashboard · Orders · Analytics · Agent Lab      │
└────────────────────────┬────────────────────────────┘
                         │ HTTP / REST
┌────────────────────────▼────────────────────────────┐
│              FastAPI Backend  (port 8000)            │
│   ┌──────────┐   ┌──────────┐   ┌──────────────┐   │
│   │ Orders   │   │  Agents  │   │  Dashboard   │   │
│   │   API    │   │   API    │   │     API      │   │
│   └────┬─────┘   └────┬─────┘   └──────┬───────┘   │
│        │              │                 │            │
│   ┌────▼──────────────▼─────────────────▼──────┐   │
│   │           Agent Orchestrator (CrewAI)       │   │
│   │   ┌──────────────┐   ┌──────────────────┐  │   │
│   │   │ Shield Agent │   │  Recovery Agent  │  │   │
│   │   │  (CrewAI)    │   │   (CrewAI)       │  │   │
│   │   └──────┬───────┘   └───────┬──────────┘  │   │
│   │          │                   │              │   │
│   │   ┌──────▼───────────────────▼──────────┐  │   │
│   │   │            Agent Tools              │  │   │
│   │   │  • Address Validator                │  │   │
│   │   │  • Risk Scorer                      │  │   │
│   │   │  • WhatsApp Sender (Twilio)         │  │   │
│   │   │  • Razorpay Payment Links           │  │   │
│   │   │  • Inventory Manager                │  │   │
│   │   └─────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────┘
                         │
           ┌─────────────▼─────────────┐
           │     PostgreSQL Database   │
           │  Orders · Customers ·     │
           │  Addresses · Products ·   │
           │  AgentActions · Discounts │
           └───────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+ |
| **AI Agents** | CrewAI |
| **LLM** | Anthropic Claude (or OpenAI) |
| **Database** | PostgreSQL |
| **Migrations** | Alembic |
| **Messaging** | Twilio (WhatsApp) |
| **Payments** | Razorpay |
| **Containerization** | Docker, Docker Compose |

---

## 📁 Project Structure

```
merchant-loss-shield/
├── backend/
│   ├── agents/              # CrewAI agent definitions
│   │   ├── shield_agent.py
│   │   └── recovery_agent.py
│   ├── tools/               # Agent tools (address, risk, payments)
│   ├── routers/             # FastAPI route handlers
│   │   ├── orders.py
│   │   ├── agents.py
│   │   └── dashboard.py
│   ├── models.py            # SQLAlchemy models
│   └── main.py              # FastAPI app entry point
├── frontend/
│   └── react-app/           # React + Vite frontend
│       ├── src/
│       │   ├── components/  # Reusable UI components
│       │   ├── pages/       # Route pages
│       │   └── api/         # API client layer
│       ├── package.json
│       └── vite.config.js
├── alembic/                 # Database migration scripts
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── alembic.ini
└── .env.example
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- An LLM API key — Anthropic Claude or OpenAI

### 1. Clone & configure

```bash
git clone https://github.com/Argon2023daiict/merchant-loss-shield.git
cd merchant-loss-shield
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)
```

### 2. Launch with Docker

```bash
docker-compose up -d
```

This starts:
- React frontend → `http://localhost:3000`
- FastAPI backend → `http://localhost:8000`
- PostgreSQL → `localhost:5432`

### 3. Try the demo flow

```bash
# Step 1 — Create a COD order for a high-risk customer
curl -X POST http://localhost:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_phone": "+919876543215",
    "items": [{"product_sku": "ELEC-001", "quantity": 1}],
    "payment_method": "cod"
  }'

# Step 2 — Run Shield Agent risk assessment
curl -X POST http://localhost:8000/api/agents/assess/{order_id}

# Step 3 — Simulate an RTO event
curl -X POST http://localhost:8000/api/orders/{order_id}/simulate-rto

# Step 4 — Run Recovery Agent
curl -X POST http://localhost:8000/api/agents/recover/{order_id}

# Step 5 — Chat with the dashboard AI
curl -X POST http://localhost:8000/api/dashboard/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top 5 high-risk COD orders today?"}'
```

---

## ⚛️ React Frontend

The React app lives in `frontend/react-app` and is the primary UI for the platform.

### Running locally (without Docker)

```bash
cd frontend/react-app
npm install
npm run dev
```

Open `http://localhost:3000`. The app proxies API calls to the FastAPI backend at `http://localhost:8000`.

### Building for production

```bash
npm run build
# Output in frontend/react-app/dist/
```

### Key pages

| Route | Description |
|---|---|
| `/` | Dashboard — KPIs, RTO rate chart, recent activity |
| `/orders` | Order list with risk scores and agent status |
| `/orders/:id` | Order detail — timeline, agent decisions, recovery status |
| `/agents` | Agent Lab — manually trigger assessments and recovery |
| `/analytics` | Revenue impact and RTO trend analysis |

### Connecting to the backend

The API base URL is configured via environment variable:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 📡 API Reference

### Orders

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/orders/` | Create a new order |
| `GET` | `/api/orders/` | List all orders |
| `GET` | `/api/orders/{id}` | Get order detail |
| `POST` | `/api/orders/{id}/simulate-rto` | Simulate an RTO event |

### Agents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/agents/assess/{order_id}` | Run Shield Agent on an order |
| `POST` | `/api/agents/recover/{order_id}` | Run Recovery Agent on an RTO order |
| `GET` | `/api/agents/actions/{order_id}` | Get agent action history |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/dashboard/chat` | Chat with the AI dashboard assistant |
| `GET` | `/api/dashboard/analytics` | Get KPIs and summary stats |

Full interactive docs available at `http://localhost:8000/docs` (Swagger UI) once the backend is running.

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# LLM (choose one)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...          # optional alternative

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rto_shield

# Twilio (WhatsApp messaging)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Razorpay (payment links)
RAZORPAY_KEY_ID=rzp_...
RAZORPAY_KEY_SECRET=...

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

---




## 🤝 Contributing

1. Fork the repository
2. Create a feature branch — `git checkout -b feature/your-feature`
3. Commit your changes — `git commit -m 'Add some feature'`
4. Push to the branch — `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">Built with ❤️ at DAIICT · Inspired by <a href="https://razorpay.com/rto/">Razorpay RTO Shield</a></p>
