# StockPilot AI — System Architecture & Design Document

## 1. Executive Overview
**StockPilot AI** is an AI-powered inventory and procurement workflow automation platform. It is designed to interpret natural language inventory queries, analyze stock levels against reorder thresholds, generate draft purchase order proposals, request Human-in-the-Loop (HITL) approval, and safely execute transactions via audited tool calls.

---

## 2. Realistic MVP Scope

### In-Scope for MVP
1. **Natural Language Interface & Intent Parser:**
   - Query stock levels, low-stock warnings, and supplier details via conversational UI.
   - Request automated inventory audits and replenishment proposal generation.
2. **Deterministic Data Query & Reorder Analysis:**
   - Automated detection of products where `current_stock <= reorder_point`.
   - Dynamic calculation of suggested order quantities based on `reorder_quantity` or `(max_stock - current_stock)`.
3. **Structured Purchase Proposal Generation:**
   - Multi-supplier identification (matching supplier catalog with low-stock SKUs).
   - Structured Draft Purchase Orders (POs) created with explicit status `DRAFT_PENDING_APPROVAL`.
4. **Human-in-the-Loop (HITL) State Machine:**
   - LangGraph interrupt/checkpointing mechanism that halts execution before external/database-modifying mutations.
   - Web UI modal for managers to review, adjust quantities/prices, approve, or reject proposals.
5. **Safe Tool Execution & Audit Trails:**
   - Read-only tools for analytics & querying.
   - Write/Transactional tools gated strictly behind approved tokens/states.
   - Complete ledger/audit log of agent thoughts, tool inputs, outputs, and user approvals.
6. **Configurable LLM Provider Adapter:**
   - Support for Ollama (local e.g. Llama 3 / Mistral / Qwen) and Cloud APIs (OpenAI / Gemini / Groq / Anthropic) through standard OpenAI-compatible or LangChain model interfaces.

### Explicitly Out-of-Scope for MVP (Deferred to Future Phases)
- Full ERP integrations (SAP, Oracle Netsuite).
- Direct banking/payment gateway processing.
- Multi-warehouse real-time routing optimization.
- Complex multi-agent negotiations across external supplier endpoints.

---

## 3. High-Level System Architecture

The system is designed as a **Modular Monolith** with an asynchronous backend and a Next.js front-end.

```
+-------------------------------------------------------------+
|               Next.js Frontend (React + TypeScript)         |
|   - Chat Interface (NL queries & streaming responses)       |
|   - Inventory & PO Dashboards                               |
|   - Human-in-the-Loop Approval & Modification Modal         |
+------------------------------+------------------------------+
                               | REST / SSE / WebSockets
                               v
+-------------------------------------------------------------+
|                 FastAPI Application Layer                   |
|   - Auth & Role-Based Access Control (RBAC)                 |
|   - REST Endpoints (Inventory, Orders, Audit Logs)          |
|   - Agent Orchestration Router & Streaming Endpoints        |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|         LangGraph Agent Workflow (StateGraph Engine)         |
|   - Intent Classifier & Router                              |
|   - Data Retrieval Tools (Read-Only)                        |
|   - Replenishment Calculation Engine                        |
|   - Human-in-the-Loop Interrupter & Checkpointer            |
|   - Transactional Mutation Tools (Gated Write)              |
+------------------------------+------------------------------+
         |                                           |
         v                                           v
+-----------------------+                 +--------------------+
|  LLM Provider Adapter |                 | PostgreSQL DB      |
|  - Ollama (Local)     |                 | - Inventory Models |
|  - Cloud (Groq/Gemini)|                 | - LangGraph States |
|  - OpenAI-compatible  |                 | - Audit Logs       |
+-----------------------+                 +--------------------+
```

---

## 4. Component Responsibilities

| Component | Technology | Responsibilities |
|---|---|---|
| **API Gateway / Server** | FastAPI (Python 3.11+) | Validates incoming payloads (Pydantic), manages user sessions, exposes endpoints for data and agent interaction. |
| **Agent Workflow Engine** | LangGraph & LangChain | Manages cyclical agent state, node routing, tool execution cycles, and pause/resume logic for human reviews. |
| **State Persistence** | PostgreSQL (Async SQLAlchemy) | Stores relational business data (Products, Suppliers, Orders) alongside LangGraph checkpoint states. |
| **Tool Execution Layer** | Python Type-Safe Callables | Encapsulates database queries and mutations. Enforces safety boundaries (read vs. write permissions). |
| **LLM Adapter** | LangChain Chat Models | Pluggable interface enabling zero-code-change switching between local (Ollama) and cloud LLMs. |
| **Frontend UI** | Next.js 14+ (App Router), TailwindCSS, Shadcn UI | Renders live conversational chat, real-time inventory metrics, and interactive approval cards. |

---

## 5. Database Schema & Entity Relationships

```
+----------------+          +-----------------------+          +----------------+
|    Supplier    | 1      * |   SupplierProduct     | *      1 |    Product     |
+----------------+----------+-----------------------+----------+----------------+
| id (PK)        |          | id (PK)               |          | id (PK)        |
| name           |          | supplier_id (FK)      |          | sku (Unique)   |
| email          |          | product_id (FK)       |          | name           |
| lead_time_days |          | unit_cost             |          | current_stock  |
| rating         |          | min_order_qty         |          | reorder_point  |
+----------------+          +-----------------------+          | max_stock      |
                                                               | unit_price     |
                                                               +-------+--------+
                                                                       | 1
                                                                       |
                                                                       | *
+----------------+ 1      * +-----------------------+ *      1 +-------v--------+
| PurchaseOrder  +----------+   PurchaseOrderItem   +----------+                |
+----------------+          +-----------------------+          +----------------+
| id (PK)        |          | id (PK)               |
| order_number   |          | purchase_order_id(FK) |
| supplier_id(FK)|          | product_id (FK)       |
| status         |          | quantity              |
| total_amount   |          | unit_cost             |
| created_by     |          +-----------------------+
| approved_by    |
| created_at     |
+-------+--------+
        | 1
        |
        | *
+-------v--------+
|   AuditLog     |
+----------------+
| id (PK)        |
| event_type     |
| actor (AI/User)|
| payload_json   |
| timestamp      |
+----------------+
```

### Entity Details:
1. **Product**: Tracks catalog, current inventory, safety thresholds (`reorder_point`), and target ceiling (`max_stock`).
2. **Supplier**: Contains vendor details, turnaround lead times, and reliability metrics.
3. **SupplierProduct**: Resolves the many-to-many relationship between suppliers and products, capturing supplier-specific unit pricing and minimum order quantities.
4. **PurchaseOrder & PurchaseOrderItem**: Represents procurement drafts, approved orders, and fulfilled stock requests.
   - Statuses: `DRAFT_PENDING_APPROVAL` -> `APPROVED` / `REJECTED` -> `ORDERED` -> `RECEIVED` -> `CANCELLED`.
5. **AuditLog**: Immutably records every tool call, agent thought/proposal, and human approval/rejection.

---

## 6. Agent Workflow & Tool Boundaries

```
[User Input] --> [Intent Classifier]
                        |
            +-----------+-----------+
            |                       |
            v                       v
     [General Query]         [Procurement Flow]
            |                       |
            v                       v
   (Read-only Tools)         (Check Stock Levels)
            |                       |
            v                       v
     [Format Reply]          [Identify Low Stock Items]
                                    |
                                    v
                             [Select Best Suppliers]
                                    |
                                    v
                             [Generate PO Draft]
                                    |
                                    v
                           ===[ HITL INTERRUPT ]===
                           (Wait for Human Approval)
                                    |
                    +---------------+---------------+
                    |                               |
                    v (Approved)                    v (Rejected/Modified)
            (Execute PO Creation)             [Cancel or Adjust Draft]
                    |                               |
                    v                               v
             [Log Audit Record]              [Log Audit Record]
                    |                               |
                    +---------------+---------------+
                                    |
                                    v
                             [Final Output]
```

### Tool Segregation & Safety Boundaries

| Tool Name | Type | Authorization Level | Description |
|---|---|---|---|
| `get_product_stock` | Read-only | Public / Automated | Retrieves product stock, reorder levels, and categories. |
| `list_low_stock_items` | Read-only | Public / Automated | Returns all items where `current_stock <= reorder_point`. |
| `get_supplier_catalog` | Read-only | Public / Automated | Fetches pricing and lead times for given suppliers. |
| `generate_po_proposal` | Analytical | Automated (Draft only) | Computes suggested order sizes and formats a structured proposal. |
| `execute_purchase_order` | Transactional | **Human Approval Required** | Commits purchase order to database as `APPROVED`/`ORDERED`. |
| `update_inventory_stock`| Transactional | **Human Approval Required** | Adjusts stock levels upon shipment receipt or manual correction. |

---

## 7. Security, Reliability & Failure Recovery

1. **Deterministic Guardrails:**
   - Quantities and prices calculated by the LLM are validated against mathematical constraints via Pydantic validators before proposing to the human.
2. **Idempotency:**
   - PO creation requests carry a unique transaction ID (`client_token` / `idempotency_key`) to prevent duplicate purchase orders on retry or connection timeouts.
3. **Database Transactions (`Unit of Work`):**
   - All multi-table write operations (e.g. PO creation + Audit logging) execute inside atomic database transactions (`async with session.begin()`).
4. **Resilient LLM Callbacks:**
   - If an LLM returns malformed JSON for a tool call, LangGraph routes to a retry/repair node rather than crashing the request.
5. **No Blind Code Execution:**
   - The agent never uses arbitrary code execution or raw SQL generators. All database interactions occur via explicit, statically-typed Python tool functions.

---

## 8. Development & Environment Configuration

### LLM Adapter Strategy
- **Local Development:** [Ollama](https://ollama.com/) running `llama3.1:8b` or `qwen2.5:7b` (zero cost, runs offline).
- **Free/Affordable Cloud Development:** Groq (Llama-3.3-70b, fast inference) or Google Gemini 2.0 Flash (free tier API).
- Switchable via a single environment variable `LLM_PROVIDER=ollama|groq|gemini|openai` in `.env`.
