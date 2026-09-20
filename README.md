# StockPilot AI 📦🤖

> **AI-powered Inventory & Procurement Workflow Automation with Human-in-the-Loop Safeguards**

StockPilot AI is an autonomous yet safely constrained inventory management copilot built with **FastAPI**, **SQLAlchemy 2.0 Async**, **PostgreSQL**, **Groq LLM (LLaMA 3.3 / GPT-OSS)**, **LangGraph State Machine**, and **Next.js**. It automates stock audits, supplier selection, and purchase order drafting while ensuring all financial mutations remain strictly gated by human approval.

---

## 🏗️ Architecture & Component Responsibilities

For the complete technical specification, data dictionary, and security model, see:
👉 [docs/architecture.md](docs/architecture.md)

### Key Design Highlights:
- **Modular Monolith:** Single unified backend service with clear separation between API routes, Pydantic schemas, database models, business services, and agent tool execution.
- **LangGraph State Machine:** Explicit `StateGraph` workflow (`intent_analyzer` -> `agent_reasoner` -> `tool_validator` -> `tool_executor` -> `response_formatter`) with loop detection and conditional routing.
- **Durable Checkpointing:** Session persistence with PostgreSQL (`AsyncPostgresSaver`) allowing multi-turn memory and thread state retrieval.
- **Deterministic Tool Calling:** The LLM does not generate raw SQL or hallucinate inventory balances. It invokes typed, validated Python tools and bases responses strictly on returned database rows.
- **Strict Financial Boundaries:** Creating a purchase request leaves it in `DRAFT` status. No financial purchase orders are issued without explicit human approval.

---

## 🤖 LangGraph Agent State Machine

```
[ User Prompt ]
      │
      ▼
[ intent_analyzer ] ─── extracts intent (e.g. LOW_STOCK_AUDIT, DRAFT_PURCHASE_REQUEST)
      │
      ▼
[ agent_reasoner ] <───┐ (Iterative tool-calling loop)
      │                │
      ├────────────────┼────────────────────────┐
      │ (Tool Calls)   │                        │ (Direct Reply / Finished)
      ▼                │                        ▼
[ tool_validator ]     │               [ response_formatter ]
      │                │                        │
      ├── (Valid)      │                        ▼
      ▼                │                   [ Final Reply ]
[ tool_executor ] ─────┘
      │ (Runs on PostgreSQL)
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

# 4. Run backend tests (47 passing tests)
pytest -v

# 5. Start FastAPI Server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🗺️ Implementation Roadmap

- [x] **Phase 0: Project Setup & System Architecture**
- [x] **Phase 1: Database & FastAPI Foundation**
- [x] **Phase 2: Inventory Business Logic & Agent Tools Layer**
- [x] **Phase 3: LLM Integration & Conversational Tool Calling**
- [x] **Phase 4: LangGraph Workflow Orchestration & State Checkpointing**
- [ ] **Phase 5: Human-in-the-Loop (HITL) Approval Workflow & PO Execution** (LangGraph interrupt() breakpoints, manager review API, PO state machine)
- [ ] **Phase 6: Next.js Frontend Dashboard & Conversational Copilot UI**
- [ ] **Phase 7: End-to-End Integration, Dockerization & Portfolio Polish**
