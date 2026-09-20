# StockPilot AI 📦🤖

> **Enterprise-Grade AI Inventory & Procurement Copilot with Human-in-the-Loop Safeguards**

StockPilot AI is an autonomous, reliable inventory management and procurement system built with **FastAPI**, **SQLAlchemy 2.0 Async**, **PostgreSQL 16**, **Groq Cloud LLM (LLaMA 3.3 70B)**, **LangGraph**, and **Next.js 15**. It automates inventory health audits, shortage detection, supplier price discovery, and draft replenishment proposals while ensuring financial transactions are strictly gated by manager authorization.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Architecture Overview](#-architecture-overview)
3. [Technology Stack](#-technology-stack)
4. [User Interface & Screenshots](#-user-interface--screenshots)
5. [Local Quickstart & Setup](#-local-quickstart--setup)
6. [Environment Configuration](#-environment-configuration)
7. [Testing & Verification](#-testing--verification)
8. [Documentation Links](#-documentation-links)
9. [Verified Features vs Known Limitations](#-verified-features-vs-known-limitations)
10. [Release Checklist](#-release-checklist)

---

## 🌟 Key Features

- **Conversational Inventory Copilot:** Natural-language assistant capable of understanding multi-criteria stock lookups, vendor searches, and replenishment requests.
- **Deterministic Business Services:** Reorder mathematics, minimum order quantity (MOQ) adjustments, and unit cost estimations are calculated via strict Python domain services, never hallucinated by LLM prompts.
- **LangGraph State Orchestration:** Cyclical `StateGraph` workflow (`intent_analyzer` ➔ `agent_reasoner` ➔ `tool_validator` ➔ `tool_executor` ➔ `response_formatter`) with loop detection guards and session state checkpointing.
- **Human-in-the-Loop (HITL) Approval Gate:** AI agents are structurally restricted to creating proposals in `DRAFT` status. Only authorized managers can review, verify, and approve financial Purchase Orders.
- **Cryptographic Hash Verification (SHA-256):** Proposals are digitally hashed upon creation; hashes are re-validated prior to order execution to guarantee line items or supplier prices were not tampered with.
- **Tool Reliability & Bounded Retries:** Idempotent read-only queries automatically retry with exponential backoff on transient DB blips; mutating operations strictly execute with `max_retries=0`.
- **Security & Privacy Hardening:** Role-Based Access Control (RBAC), prompt injection defense, SQL injection protection, sensitive credential log redaction, and `X-Request-ID` correlation tracing.

---

## 🏗️ Architecture Overview

```mermaid
flowchart TD
    User([Supermarket Operator / Procurement Manager])
    
    subgraph Presentation [Next.js 15 Frontend]
        Dashboard["Dashboard (KPIs & Alerts)"]
        Catalog["Inventory Catalog & Stock Adjuster"]
        Copilot["AI Assistant Chat Interface"]
        Approvals["Manager Approval Center"]
        AuditFeed["Security & Audit Log Ledger"]
    end

    subgraph BackendAPI [FastAPI Application Tier]
        Router["/api/v1 Endpoints"]
        Middleware["RequestCorrelationMiddleware & Log Sanitizer"]
        
        subgraph AgentEngine [LangGraph AI Orchestrator]
            Intent["intent_analyzer"] --> Reasoner["agent_reasoner"]
            Reasoner --> RouterTool{"Tool Router"}
            RouterTool -- Valid Tool --> Executor["tool_executor (@safe_tool_executor)"]
            RouterTool -- Done --> Formatter["response_formatter"]
            Executor --> Reasoner
        end
        
        subgraph Services [Domain Business Services]
            InvService["InventoryService"]
            PRService["PurchaseRequestService"]
            ApprService["ApprovalService"]
            AuditService["AuditLogService"]
        end
    end

    subgraph DataTier [Persistence & External APIs]
        Groq["Groq Cloud API (llama-3.3-70b-versatile)"]
        Postgres[(PostgreSQL 16 Database)]
        Checkpoints[(LangGraph Checkpoints)]
    end

    User <--> Presentation
    Presentation <--> Router
    Router --> Middleware --> AgentEngine
    AgentEngine <--> Groq
    AgentEngine <--> Checkpoints
    AgentEngine --> Services
    Services <--> Postgres
```

---

## 💻 Technology Stack

| Domain | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | FastAPI | `^0.110.0` | High-performance async REST API framework |
| **Agent Orchestration**| LangGraph & LangChain | `^0.0.30` | Cyclical state machine workflow and multi-turn routing |
| **LLM Inference** | Groq Cloud API | `^0.5.0` | Ultra-fast token inference (`llama-3.3-70b-versatile`) |
| **Database & ORM** | PostgreSQL 16 & SQLAlchemy | `^2.0.28` | Relational storage with asyncpg connection pooling |
| **Schema Migrations** | Alembic | `^1.13.1` | Declarative database migration versioning |
| **Frontend Framework**| Next.js (App Router) | `15.1.4` | React 19 server/client components and UI pages |
| **Styling & Icons** | Tailwind CSS & Lucide React | `^3.4.17` | Responsive dark/light theme dashboard styling |
| **Containerization** | Docker & Docker Compose | `v2+` | Multi-stage container packaging for all 3 tiers |

---

## 🖼️ User Interface & Screenshots

| Page | View Description | Placeholder |
| :--- | :--- | :---: |
| **Executive Dashboard** | Real-time KPI summaries, low-stock alerts, procurement spend trends | `[Dashboard Screenshot]` |
| **Inventory Management**| Filterable catalog, stock levels, warehouse coordinates, reorder math | `[Inventory Screenshot]` |
| **Conversational Copilot** | Natural language queries, live tool execution traces, proposal cards | `[AI Assistant Screenshot]` |
| **Approval Center** | Role-gated queue, SHA-256 hash validation, single-click PO issuance | `[Approvals Screenshot]` |
| **Audit Ledger** | Append-only compliance log with JSON before/after state diff inspection | `[Audit Trail Screenshot]` |

---

## ⚡ Local Quickstart & Setup

### Option A: Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/stockpilot-ai.git
cd stockpilot-ai

# 2. Configure environment variables
cp .env.example .env
# Edit .env and supply your GROQ_API_KEY

# 3. Launch all services (PostgreSQL, Backend, and Frontend)
docker compose up --build -d

# 4. Access the applications
# Frontend Dashboard: http://localhost:3000
# Backend OpenAPI Docs: http://localhost:8000/docs
# Backend Health Check: http://localhost:8000/api/v1/health
```

### Option B: Local Python Virtual Environment & Node.js

```powershell
# 1. Start PostgreSQL via Docker
docker compose up postgres -d

# 2. Setup Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env

# Apply migrations and seed initial supermarket data
alembic upgrade head
python scripts/seed_data.py

# Start Backend Server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 3. Setup Frontend (in a new terminal)
cd ../frontend
npm install
cp .env.example .env.local
npm run dev
# Open http://localhost:3000
```

---

## ⚙️ Environment Configuration

### Root / Backend `.env` Template
```ini
ENVIRONMENT=development
DEBUG=true
PROJECT_NAME="StockPilot AI"
API_V1_PREFIX="/api/v1"

POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=stockpilot_db
POSTGRES_USER=stockpilot
POSTGRES_PASSWORD=stockpilot_password
DATABASE_URL=postgresql+asyncpg://stockpilot:stockpilot_password@localhost:5432/stockpilot_db

BACKEND_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

LLM_PROVIDER=groq
LLM_MODEL_NAME=llama-3.3-70b-versatile
GROQ_API_KEY=your_groq_api_key_here
```

### Frontend `.env.local` Template
```ini
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
PORT=3000
```

---

## 🧪 Testing & Verification

### Backend Automated Test Suite (85 Tests)
```powershell
cd backend
.\.venv\Scripts\pytest -v
```
- **Unit Tests:** Business logic, reorder formulas, LLM adapter, agent state transitions.
- **Integration Tests:** REST endpoints, inventory adjustments, approval lifecycle, audit trails.
- **Evaluation Benchmark:** 12 benchmark cases verifying intent accuracy and tool mapping.
- **Reliability Tests:** Timeout protection, bounded retries, and failure injection.
- **Security Tests:** RBAC enforcement, self-approval prevention, SHA-256 hash checks, log sanitization.

### Frontend Test Suite (7 Tests)
```powershell
cd frontend
npm run test
```

---

## 📚 Documentation Links

- 🏛️ [System Architecture & Design](docs/architecture.md)
- 🗄️ [Database Schema & Data Dictionary](docs/database-schema.md)
- 🤖 [LangGraph Workflow & Tool Orchestration](docs/agent-workflow.md)
- 🔒 [Security Review & STRIDE Threat Model](docs/security.md)
- 📊 [Agent Evaluation Benchmark Report](docs/evaluation.md)
- 🚀 [Deployment & Infrastructure Guide](docs/deployment.md)
- 🛡️ [Reliability & Failure Recovery Report](docs/reliability_report.md)

---

## 🔍 Verified Features vs Known Limitations

### ✅ Verified Features (Locally Tested)
- **Deterministic Reorder Recommendations:** Evaluated against 25 product SKUs with supplier MOQ constraints.
- **LangGraph Tool Loop:** Verified with Groq LLM and mock adapters; prevents infinite looping via bounded iterations.
- **Cryptographic Approval Gate:** Verified preventing parameter tampering via SHA-256 mismatch detection.
- **RBAC Security:** Verified denying operator approval attempts with HTTP 403 Forbidden.
- **Structured Log Sanitization:** Verified scrubbing API keys and passwords from log records.

### ⚠️ Known Limitations & Deployment Scope
- **Checkpointer Backend:** Default development setup uses in-memory/async thread state; production multi-instance clustering requires Redis or PostgreSQL checkpointer.
- **Free-Tier Cold Starts:** Deploying on free serverless containers (e.g. Render Free) introduces a 50s cold-start latency if idle.
- **External EDI Integration:** Supplier PO dispatch is implemented via `MockProcurementClient` and requires production EDI/ERP adapter configuration.

---

## 📋 Release Checklist

- [x] All 85 backend tests passing (`pytest -v`).
- [x] All 7 frontend Vitest tests passing (`npm run test`).
- [x] Frontend production build verified (`npm run build`).
- [x] Multi-stage Dockerfiles created for Backend and Frontend.
- [x] Docker Compose configured with healthchecks, non-root users, and volumes.
- [x] Database migrations and reset procedures tested cleanly (`reset_db.py`).
- [x] Zero hardcoded secrets in repository.
- [x] Complete technical documentation suite generated in `docs/`.
