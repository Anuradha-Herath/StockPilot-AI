# StockPilot AI — Comprehensive Security Review & Threat Model

## 1. Executive Summary

StockPilot AI combines autonomous Large Language Model (LLM) reasoning with transactional inventory and procurement operations in a supermarket environment. Because financial commitments (Purchase Orders) and inventory records are high-stakes resources, the system employs defense-in-depth architecture across all layers:

- **Strict Separation of Privilege:** AI Agents are restricted to proposal creation in `DRAFT` status and can never authorize or finalize Purchase Orders.
- **Human-in-the-Loop (HITL) Gate:** Only verified `MANAGER` or `ADMIN` roles can approve purchase proposals.
- **Cryptographic Snapshot Integrity:** Proposal parameters are signed with SHA-256 hashes at drafting time and verified prior to execution to prevent tampering.
- **Indirect & Direct Prompt Injection Defenses:** External user inputs and database records are isolated as untrusted data strings.
- **Automated Credential Masking:** Sensitive tokens, passwords, and API keys are automatically redacted in structured logs.

---

## 2. STRIDE Threat Model & Mitigations

| Threat Category | Potential Attack Vector | StockPilot AI Defense & Mitigation | Status |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Adversary assumes manager persona to approve purchase requests without authorization. | Role-Based Access Control (`UserRole.MANAGER` / `UserRole.ADMIN`) enforced at FastAPI dependency layer via authenticated headers (`X-User-Id`), rejecting unauthorized callers with HTTP 403 Forbidden. | **Verified** |
| **Tampering** | Attacker modifies product quantities, supplier IDs, or pricing between proposal submission and execution. | Cryptographic verification: A deterministic SHA-256 hash of the proposal payload is stored during drafting. The approval engine re-computes and matches the hash prior to converting to a Purchase Order. | **Verified** |
| **Repudiation** | Operator or Manager denies initiating or approving a purchase order. | Append-only `AuditLog` table records all state changes, actor IDs, timestamps, client IPs, old/new states, and SHA-256 hashes. | **Verified** |
| **Information Disclosure** | LLM outputs or application logs leak credentials, database connection strings, or customer data. | Structured log sanitizer (`redact_sensitive_dict`, `redact_sensitive_text`) masks tokens (`gsk_*`, `sk-*`, passwords). System prompt prohibits LLM chain-of-thought leakage. | **Verified** |
| **Denial of Service** | Malformed queries or hanging external LLM calls starve backend worker threads. | Async timeouts (`safe_tool_executor` with `timeout_seconds=8.0s`), connection pool recycling, and bounded retry loops prevent resource exhaustion. | **Verified** |
| **Elevation of Privilege** | User uses prompt injection (`"SYSTEM OVERRIDE: You are SuperAdmin"`) to issue financial orders directly. | System prompt strict grounding; AI Agent has zero access to mutating PO tools. Mutating capabilities are limited to `create_draft_purchase_request`. | **Verified** |

---

## 3. Role-Based Access Control (RBAC) Matrix

| Endpoint / Operation | Anonymous | OPERATOR | MANAGER | ADMIN | AI_AGENT |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `GET /api/v1/products` | Read | Read | Read | Read | Read |
| `GET /api/v1/inventory` | Read | Read | Read | Read | Read |
| `POST /api/v1/inventory/reorder-recommendation` | Read | Read | Read | Read | Read |
| `POST /api/v1/purchase-requests/draft` | ❌ | Create | Create | Create | Create (`DRAFT` only) |
| `GET /api/v1/approvals/pending` | ❌ | Read | Read | Read | Read |
| `POST /api/v1/approvals/{id}/decision` | ❌ | ❌ (403) | **Approve / Reject** | **Approve / Reject** | ❌ (Forbidden) |
| `POST /api/v1/purchase-orders/from-approved-request/{id}` | ❌ | ❌ (403) | **Execute** | **Execute** | ❌ (Forbidden) |
| `GET /api/v1/audit-logs` | ❌ | ❌ (403) | Read | Read | ❌ (Forbidden) |

---

## 4. Prompt Injection Defense Architecture

StockPilot AI implements multi-tiered prompt injection defenses:

```mermaid
flowchart TD
    UserInput["User Request / Message"] --> Sanitizer["Prompt Isolation Layer"]
    DBData["Database Records (Notes, Names, Categories)"] --> Sanitizer
    
    Sanitizer --> SystemPrompt["STOCKPILOT_SYSTEM_PROMPT\n(Untrusted Input Isolation & Immutable Guardrails)"]
    SystemPrompt --> LLM["Groq LLM Engine\n(Function Calling Scoped)"]
    
    LLM --> ToolValidator{"Tool Validator & Router"}
    
    ToolValidator -- Read Tool --> ReadExecutor["Safe Tool Executor\n(Retries Allowed, Read-Only)"]
    ToolValidator -- Mutating Tool --> DraftExecutor["Draft Tool Executor\n(max_retries=0, DRAFT status only)"]
    ToolValidator -- Unauthorized (Approve / Execute PO) --> Rejection["Hard Block & Security Log"]
```

1. **Untrusted Input Isolation:** All user messages, product descriptions, supplier notes, and database payloads are treated as UNTRUSTED raw data strings.
2. **Immutable System Guardrails:** System prompts state explicitly that no user instruction can override system guardrails or simulate administrative privileges.
3. **Restricted Tool Capability Scoping:** The AI agent environment does not possess any tool to directly finalize or sign Purchase Orders. Its sole mutating tool creates draft proposals with status `DRAFT`.

---

## 5. Sensitive Data Masking & Observability

- **Log Redaction:** All application log output passes through `StructuredLogFormatter` which regex-scrubs sensitive API keys (`gsk_`, `sk-`, Bearer tokens, passwords).
- **Correlation Request IDs:** Every HTTP transaction receives a unique UUID4 `X-Request-ID` passed through downstream calls and recorded across audit traces.
