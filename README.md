# 🛡️ RTO Shield & Recovery Agent

> An AI-powered multi-agent system that detects high-risk COD orders before they ship
> and manages post-return recovery, turning RTO losses into recovered revenue.

**Inspired by [Razorpay's RTO Shield](https://razorpay.com/rto/) and their Agentic AI 
vision with Agent Studio.**

![Architecture](https://img.shields.io/badge/Architecture-Multi--Agent-blue)
![AI](https://img.shields.io/badge/AI-CrewAI%20+%20Claude-purple)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)
![Frontend](https://img.shields.io/badge/Frontend-Streamlit-red)

---

## 🎯 The Problem

Cash on Delivery accounts for ~60% of Indian e-commerce, but carries a devastating 
side effect: **Return to Origin (RTO)**. When customers refuse delivery or addresses 
are incorrect, merchants face:

- **₹100-300 wasted** per order on forward + reverse shipping
- **25-40% RTO rates** for some product categories
- **Manual, error-prone** risk assessment processes
- **Lost revenue** from products stuck in transit

For a merchant processing 10,000 COD orders/month with a 30% RTO rate, that's 
**₹3-9 Lakhs/month** in pure shipping losses.

## 🤖 The Solution: Two AI Agents Working in Tandem

### Agent 1: 🛡️ The Shield Agent (Pre-Dispatch)
Analyzes every COD order *before* dispatch using:
- **Behavioral Analysis**: Customer history, RTO rate, account age, verification status
- **Address Intelligence**: Pincode-city validation, vague address detection, geocoding
- **Risk Scoring Engine**: Weighted composite score across 5 risk dimensions
- **Autonomous Actions**: Approve / Request verification / Recommend cancellation

### Agent 2: 🔄 The Recovery Agent (Post-Return)
Activates after RTO to salvage revenue:
- **Empathetic Re-engagement**: Personalized WhatsApp messages (not complaints!)
- **Dynamic Incentives**: LLM-generated discount codes calibrated to order value
- **Payment Link Generation**: Razorpay payment links for easy re-ordering
- **Inventory Management**: Tracks returned items through inspection pipeline

---

## 🏗️ Architecture

┌─────────────────────────────────────────────────────┐
│ Streamlit Dashboard │
│ 📊 Analytics │ 🤖 Chat │ 📦 Orders │ 🧪 Lab │
└────────────────────────┬────────────────────────────┘
│ HTTP
┌────────────────────────▼────────────────────────────┐
│ FastAPI Backend │
│ ┌─────────┐ ┌──────────┐ ┌──────────┐ │
│ │ Orders │ │ Agents │ │Dashboard │ │
│ │ API │ │ API │ │ API │ │
│ └────┬────┘ └────┬─────┘ └────┬─────┘ │
│ │ │ │ │
│ ┌────▼────────────▼──────────────▼─────┐ │
│ │ Agent Orchestrator │ │
│ │ ┌──────────┐ ┌──────────────┐ │ │
│ │ │ Shield │ │ Recovery │ │ │
│ │ │ Agent │ │ Agent │ │ │
│ │ │(CrewAI) │ │ (CrewAI) │ │ │
│ │ └──┬───────┘ └───┬──────────┘ │ │
│ │ │ │ │ │
│ │ ┌──▼────────────────▼──────────┐ │ │
│ │ │ Agent Tools │ │ │
│ │ │ • Address Validator │ │ │
│ │ │ • Risk Scorer │ │ │
│ │ │ • WhatsApp Sender (Twilio) │ │ │
│ │ │ • Razorpay Payments │ │ │
│ │ │ • Inventory Manager │ │ │
│ │ └──────────────────────────────┘ │ │
│ └──────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────┘
│
┌─────────────▼─────────────┐
│ PostgreSQL Database │
│ Orders • Customers • │
│ Addresses • Products • │
│ AgentActions • Discounts │
└───────────────────────────┘


## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- An LLM API key (Anthropic Claude or OpenAI)

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/rto-shield-recovery.git
cd rto-shield-recovery
cp .env.example .env
# Edit .env with your API keys


2. Launch everything

docker-compose up -d

3. Try the demo  

# 1. Create a COD order for a high-risk customer
curl -X POST http://localhost:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_phone": "+919876543215",
    "items": [{"product_sku": "ELEC-001", "quantity": 1}],
    "payment_method": "cod"
  }'

# 2. Run Shield Agent assessment
curl -X POST http://localhost:8000/api/agents/assess/{order_id}

# 3. Simulate RTO
curl -X POST http://localhost:8000/api/orders/{order_id}/simulate-rto

# 4. Run Recovery Agent
curl -X POST http://localhost:8000/api/agents/recover/{order_id}

# 5. Chat with the dashboard
curl -X POST http://localhost:8000/api/dashboard/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top 5 high-risk COD orders today?"}'

---

## 🧩 React UI
A new React dashboard is available in `frontend/react-app`.

To run it:

```bash
cd frontend/react-app
npm install
npm run dev
```

Then open `http://localhost:3000` in your browser. The React app talks to the FastAPI backend at `http://localhost:8000` and uses the existing database-backed APIs.

