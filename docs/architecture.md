# StockPilot AI — System Architecture & Design Document

## 1. Executive Overview

**StockPilot AI** is an enterprise-grade autonomous inventory management and procurement copilot designed for supermarket retail chains. It combines conversational Large Language Model (LLM) reasoning with transactional database operations, enforcing deterministic business logic, strict security guardrails, and Human-in-the-Loop (HITL) approval gates before executing financial commitments.

---

## 2. High-Level System Architecture

The system is structured as a decoupled 3-tier architecture:

```mermaid
flowchart TD
    User([Supermarket Operator / Procurement Manager])
    
    subgraph Frontend [Next.js 15 Presentation Tier]
        UI[React 19 Tailwind CSS Dashboard]
        PersonaSwitcher[Role Switcher: OPERATOR / MANAGER / ADMIN]
        ChatWidget[Conversational Assistant Interface]
        ApprovalTable[Human-in-the-Loop Approval Queue]
    end

    subgraph Backend [FastAPI Application Tier]
        Router[API V1 Router]
        CorrelationMiddleware[RequestCorrelationMiddleware & Log Sanitizer]
        AuthDeps[RBAC & Persona Dependency Injection]
        
        subgraph LangGraphOrchestrator [LangGraph AI Agent Engine]
            IntentNode[intent_analyzer]
            ReasonerNode[agent_reasoner]
            ValidatorNode[tool_validator]
            ExecutorNode[tool_executor]
            FormatterNode[response_formatter]
            Checkpointer[(PostgreSQL AsyncPostgresSaver)]
        end
        
        subgraph BusinessServices [Transactional Service Layer]
            ProdService[ProductService]
            InvService[InventoryService]
            PRService[PurchaseRequestService]
            ApprovalService[ApprovalService]
            POService[PurchaseOrderService]
            AuditService[AuditLogService]
        end
    end

    subgraph ExternalServices [External Integrations]
        GroqLLM[Groq Cloud API: llama-3.3-70b-versatile]
        MockEDI[Mock Supplier Procurement Gateway]
    end

    subgraph DatabaseTier [Data & Persistence Tier]
        Postgres[(PostgreSQL 16 Database)]
    end

    User <--> UI
    UI <--> Router
    Router --> CorrelationMiddleware --> AuthDeps
    AuthDeps --> LangGraphOrchestrator
    AuthDeps --> BusinessServices
    
    LangGraphOrchestrator <--> GroqLLM
    LangGraphOrchestrator <--> Checkpointer
    LangGraphOrchestrator --> BusinessServices
    
    BusinessServices --> MockEDI
    BusinessServices <--> Postgres
    Checkpointer <--> Postgres
```

---

## 3. Core Architectural Subsystems

### 3.1 Presentation Tier (Next.js 15)
- **Framework:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons.
- **Pages:**
  - `/` (Dashboard): Real-time KPI cards (Total SKUs, Low Stock, Pending Approvals, Total Value) and recent procurement activity.
  - `/inventory`: Paginated, searchable product inventory table with stock status badges and quick reorder calculator.
  - `/assistant`: Interactive chat copilot with real-time tool execution tracking and draft purchase proposal cards.
  - `/approvals`: Manager queue with cryptographic SHA-256 proposal hash verification and single-click Approve / Reject actions.
  - `/audit`: Immutable security and operation audit trail ledger.
- **Client Features:** User persona switching (`MANAGER`, `OPERATOR`, `ADMIN`) injecting simulated authenticated `X-User-Id` headers.

### 3.2 Application & Agent Tier (FastAPI + LangGraph)
- **Framework:** FastAPI, Pydantic V2, LangGraph, LangChain Core.
- **Agent Workflow:** Cyclical StateGraph with bounded iterations (max 5 iterations), preventing infinite loops.
- **Checkpointing:** State persistence via `AsyncPostgresSaver` associating state with unique `thread_id` sessions.
- **Reliability Wrapper:** `@safe_tool_executor` providing timeout protection (`asyncio.wait_for`), bounded retries for read queries, and exception trapping.

### 3.3 Data Tier (PostgreSQL 16)
- **ORM & Migrations:** SQLAlchemy 2.0 (Async Engine + asyncpg), Alembic migrations.
- **Integrity Constraints:** Database-level `CHECK` constraints on stock quantities, non-negative unit costs, ratings, and unique SKU/Supplier codes.
- **Audit Logging:** Append-only ledger recording every user and AI state transition with actor IDs, IP addresses, and state diff payloads.

---

## 4. End-to-End Data & Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor Manager as Procurement Manager
    participant UI as Next.js Assistant
    participant API as FastAPI /api/v1/chat
    participant Graph as LangGraph Orchestrator
    participant LLM as Groq LLM (llama-3.3-70b)
    participant Tools as Agent Tool Layer
    participant DB as PostgreSQL Database
    participant Approvals as Approval Engine

    Manager->>UI: "Check low stock and create a draft PR for whole milk"
    UI->>API: POST /api/v1/chat (thread_id="t-101", user_id="sarah_manager")
    API->>Graph: Execute StateGraph
    Graph->>LLM: Analyze intent & select tools
    LLM-->>Graph: Call find_low_stock_products(category='Dairy')
    Graph->>Tools: execute(find_low_stock_products)
    Tools->>DB: SELECT * FROM inventory_levels WHERE current_stock <= reorder_point
    DB-->>Tools: [Whole Milk: Stock=8, ReorderPoint=20, Deficit=12]
    Tools-->>Graph: ToolResult.ok(...)
    Graph->>LLM: Analyze deficit & suggest draft PR
    LLM-->>Graph: Call create_draft_purchase_request(supplier_id=1, qty=20)
    Graph->>Tools: execute(create_draft_purchase_request)
    Tools->>DB: INSERT INTO purchase_requests (status='DRAFT')
    DB-->>Tools: Created PR-20260920-A1B2
    Tools-->>Graph: ToolResult.ok(...)
    Graph->>LLM: Generate final markdown response
    LLM-->>Graph: Grounded markdown response with draft PR details
    Graph-->>API: Return ChatResponse
    API-->>UI: Display assistant response + Proposal card

    Manager->>UI: Clicks "Approve & Issue PO"
    UI->>Approvals: POST /api/v1/approvals/requests/{id}/approve
    Approvals->>DB: Verify SHA-256 Hash, Role & Row Lock
    Approvals->>DB: INSERT INTO purchase_orders (status='ISSUED')
    Approvals-->>UI: Order Execution Receipt
```
