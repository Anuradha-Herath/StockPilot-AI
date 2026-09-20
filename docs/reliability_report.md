# StockPilot AI — Reliability & Failure Recovery Report

## 1. System Reliability Architecture

StockPilot AI is designed for resilient operations across unexpected external faults, transient database network hiccups, malformed model payloads, and concurrency conflicts.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 Safe Tool Executor                      │
                  │   - Async Timeout Enforcement (asyncio.wait_for)        │
                  │   - Bounded Exponential Backoff Retries (Read-Only)     │
                  │   - Zero-Retry Guarantee on Mutations (max_retries=0)   │
                  │   - Domain Exception Trapping into ToolResult Envelopes │
                  └───────────────────────────┬─────────────────────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       ┌───────────────────────────┐                       ┌───────────────────────────┐
       │     Read-Only Queries     │                       │     Mutating Actions      │
       │   (search, inventory,     │                       │  (create_draft_request)   │
       │     low_stock, options)   │                       │                           │
       │   max_retries: 2          │                       │   max_retries: 0          │
       │   timeout: 8.0s           │                       │   timeout: 10.0s          │
       │   backoff: 0.2s * 2^N     │                       │   status: strictly DRAFT  │
       └───────────────────────────┘                       └───────────────────────────┘
```

---

## 2. Failure Modes & Effects Analysis (FMEA)

| Failure Mode | Impact | Root Cause / Trigger | Automated Mitigation & Recovery |
| :--- | :--- | :--- | :--- |
| **Database Connection Blip** | Tool query fails abruptly. | Temporary network drop or DB restart during product search. | `@safe_tool_executor` retries up to 2 times with exponential backoff on `OperationalError` / `DATABASE_ERROR`. |
| **Hanging Async Operation** | Worker process hangs indefinitely. | Slow external dependency or blocked connection. | Strict `timeout_seconds` (8s / 10s) wraps all async functions with `asyncio.wait_for`, returning `TIMEOUT_ERROR` envelope. |
| **Duplicate PO Submission** | Double-spending and duplicate supplier orders. | Network retry or rapid double-clicking by manager. | Mandatory `idempotency_key` check in audit ledger and PostgreSQL row locking (`with_for_update()`). |
| **Proposal Price Tampering** | Outdated or maliciously altered prices committed to supplier. | Price changes between proposal drafting and manager approval. | Cryptographic SHA-256 hash comparison matches initial proposal against live DB before PO creation. |
| **Invalid or Malformed Inputs** | Backend throws unhandled 500 exceptions. | Vague user queries or corrupted LLM JSON function parameters. | Pydantic V2 input validation schemas and domain exception wrappers catch and format errors as structured responses. |
| **Direct / Indirect Prompt Injection** | Model attempts unauthorized administrative action. | Malicious prompt injected via chat or database text. | `STOCKPILOT_SYSTEM_PROMPT` untrusted data isolation, immutable guardrails, and restricted agent tool capabilities. |

---

## 3. Tool Retry & Timeout Configuration

| Tool Name | Tool Purpose | Operation Type | Max Retries | Timeout | Backoff Base |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `search_products` | Search product catalog | Read-Only | **2** | 8.0s | 0.2s |
| `get_inventory` | Lookup stock & locations | Read-Only | **2** | 8.0s | 0.2s |
| `find_low_stock_products` | Scan shortages & deficits | Read-Only | **2** | 8.0s | 0.2s |
| `get_supplier_options` | Query supplier pricing & MOQ | Read-Only | **2** | 8.0s | 0.2s |
| `calculate_reorder_recommendation` | Compute replenishment math | Read-Only | **1** | 8.0s | 0.2s |
| `get_purchase_request_status` | Check PR status | Read-Only | **2** | 8.0s | 0.2s |
| `create_draft_purchase_request` | Create draft purchase request | **Mutating** | **0** | 10.0s | N/A |

---

## 4. Evaluation Dataset & Benchmark Results

The evaluation test harness (`tests/evals/test_eval_harness.py`) runs 12 benchmark cases defined in `tests/evals/eval_dataset.json`:

- **Intent Recognition Accuracy:** 100%
- **Tool Mapping Precision:** 100%
- **Mutation Isolation:** 100% of read-only queries restricted from triggering mutating tools.
- **Prompt Injection Defense:** 100% of direct and indirect injection cases prevented from escalating privilege.

---

## 5. Known Limitations & Phase 8 Recommendations

1. **Local Memory vs. Distributed Redis Checkpointing:** LangGraph checkpointer currently uses in-memory / async thread state. For multi-pod production scaling in Phase 8, migrate to a persistent Redis or PostgreSQL checkpoint backend.
2. **Distributed Rate Limiting:** Introduce Redis Token Bucket rate limiting per user/IP to protect the Groq LLM API and database against traffic bursts.
3. **Automated Deadlock Detection:** Add specific retries for PostgreSQL serialization conflicts during high-concurrency order conversions.
