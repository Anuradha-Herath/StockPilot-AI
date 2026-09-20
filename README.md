# StockPilot AI 📦🤖

> **AI-powered Inventory & Procurement Workflow Automation with Human-in-the-Loop Safeguards**

StockPilot AI is an autonomous yet safely constrained inventory management copilot built with **FastAPI**, **SQLAlchemy 2.0 Async**, **PostgreSQL**, **Groq LLM (LLaMA 3.3 / GPT-OSS)**, **LangChain / LangGraph**, and **Next.js**. It automates stock audits, supplier selection, and purchase order drafting while ensuring all financial mutations remain strictly gated by human approval.

---

## 🏗️ Architecture & Component Responsibilities

For the complete technical specification, data dictionary, and security model, see:
👉 [docs/architecture.md](docs/architecture.md)

### Key Design Highlights:
- **Modular Monolith:** Single unified backend service with clear separation between API routes, Pydantic schemas, database models, business services, and agent tool execution.
- **Async Database Layer:** Asynchronous SQLAlchemy 2.0 with connection pooling using `asyncpg` for high-throughput I/O.
- **Deterministic Tool Calling:** The LLM does not generate raw SQL or hallucinate inventory balances. It invokes typed, validated Python tools and bases responses strictly on returned database rows.
- **Provider Abstraction:** Dynamic adapter supporting **Groq Cloud API** (`openai/gpt-oss-120b`, `llama-3.3-70b-versatile`) and **Ollama Local** (`llama3.1:8b`).
- **Strict Financial Boundaries:** Creating a purchase request leaves it in `DRAFT` status. No financial purchase orders are issued without explicit human approval.

---

## 🤖 Phase 3: Conversational Copilot & Tool Calling Flow

```
[ User Prompt ]
      │
      ▼
[ FastAPI /api/v1/chat ]
      │
      ▼
[ AgentService Reasoning Loop ]
      │
      ├──> [ LLM (Groq API) with Bound Tools ]
      │         │
      │         ├── (Requests Tool Call: tool_name, args)
      │         ▼
      ├──> [ Tool Execution Layer ] (Type-checked via Pydantic)
      │         │
      │         ├── Runs query against PostgreSQL (AsyncSession)
      │         ▼
      ├──> [ ToolMessage Result Envelope ] (JSON data)
      │         │
      │         ▼
      └──> [ LLM Formulates Grounded Response ]
                │
                ▼
[ Final Natural Language Reply + Tool Execution Logs ]
```

---

## 🛠️ Registered Agent Tools

All tools return a structured `ToolResult[T]` envelope with `success: bool`, `data: T`, and `error: ToolError`.

| Tool Name | Type | Description | Input Schema | Output Schema |
|---|---|---|---|---|
| `search_products` | Read-only | Search catalog by SKU/name/category | `SearchProductsInput` | `SearchProductsOutput` |
| `get_inventory` | Read-only | Filter inventory by stock status (`HEALTHY`, `LOW_STOCK`, `OUT_OF_STOCK`) | `GetInventoryInput` | `GetInventoryOutput` |
| `find_low_stock_products` | Read-only | Retrieve all items below reorder threshold with deficits | `FindLowStockProductsInput` | `FindLowStockProductsOutput` |
| `get_supplier_options` | Read-only | Look up supplier pricing, ratings, lead times, and MOQs for a SKU | `GetSupplierOptionsInput` | `GetSupplierOptionsOutput` |
| `calculate_reorder_recommendation` | Analytical | Compute replenishment quantity, MOQ adjustments & costs | `CalculateReorderRecommendationInput` | `CalculateReorderRecommendationOutput` |
| `create_draft_purchase_request` | Safe Mutation | Create a `DRAFT` request for manager review | `CreateDraftPurchaseRequestInput` | `CreateDraftPurchaseRequestOutput` |
| `get_purchase_request_status` | Read-only | Check approval status and item breakdown by PR number/ID | `GetPurchaseRequestStatusInput` | `GetPurchaseRequestStatusOutput` |

---

## ⚡ Quickstart & Setup Guide (Windows PowerShell)

```powershell
# 1. Start PostgreSQL
docker compose up -d

# 2. Activate virtual environment & run migrations
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head

# 3. Seed supermarket database
python scripts/seed_data.py

# 4. Run backend tests (43 passing tests)
pytest -v

# 5. Start FastAPI Server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🧪 Live Manual Test Suite Examples

### 1. Low Stock Inquiry
```powershell
$body = @{ message = "Show me products that are running low in the dairy category." } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/chat" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5
```

### 2. Supplier Lookup
```powershell
$body = @{ message = "Which suppliers can provide whole milk?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/chat" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5
```

### 3. Draft Purchase Request Creation
```powershell
$body = @{ message = "Prepare a draft purchase request for low-stock whole milk with 50 units." } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/chat" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5
```

### 4. Purchase Request Status Check
```powershell
$body = @{ message = "What is the status of purchase request 1?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/chat" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5
```

---

## 🗺️ Implementation Roadmap

- [x] **Phase 0: Project Setup & System Architecture**
- [x] **Phase 1: Database & FastAPI Foundation**
- [x] **Phase 2: Inventory Business Logic & Agent Tools Layer**
- [x] **Phase 3: LLM Integration & Conversational Tool Calling**
- [ ] **Phase 4: Human-in-the-Loop (HITL) Workflow & LangGraph State Machine** (LangGraph Checkpoints, interrupt() nodes, PO approval state machine)
- [ ] **Phase 5: Next.js Frontend Dashboard & Conversational Copilot UI**
- [ ] **Phase 6: End-to-End Integration, Dockerization & Portfolio Polish**
