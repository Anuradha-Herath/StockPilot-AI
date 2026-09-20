# StockPilot AI — Security Architecture & Governance

## 1. Security Principles

StockPilot AI adheres to five core security pillars:
1. **Least Privilege & Role Boundaries:** The AI Agent is strictly limited to information retrieval and draft creation (`DRAFT` status). It cannot execute or approve financial orders.
2. **Human-in-the-Loop Verification:** Financial commitments require explicit human manager authorization with role validation (`MANAGER` or `ADMIN`).
3. **Cryptographic State Integrity:** Proposal payloads are signed with canonical SHA-256 hashes to prevent modification between drafting and execution.
4. **Input Isolation & Prompt Hardening:** External prompts and database records are treated as untrusted strings to prevent direct and indirect prompt injection.
5. **Continuous Auditability:** All operations are recorded in an append-only audit ledger with actor types, IP addresses, and state diffs.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint / Operation | Anonymous | OPERATOR | MANAGER | ADMIN | AI_AGENT |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `GET /api/v1/products` | Read | Read | Read | Read | Read |
| `GET /api/v1/inventory` | Read | Read | Read | Read | Read |
| `POST /api/v1/purchase-requests/draft` | ❌ | Create | Create | Create | Create (`DRAFT` only) |
| `GET /api/v1/approvals/pending` | ❌ | Read | Read | Read | Read |
| `POST /api/v1/approvals/requests/{id}/approve` | ❌ | ❌ (403) | **Approve & Execute** | **Approve & Execute** | ❌ (Forbidden) |
| `POST /api/v1/approvals/requests/{id}/reject` | ❌ | ❌ (403) | **Reject** | **Reject** | ❌ (Forbidden) |
| `GET /api/v1/audit-logs` | ❌ | ❌ (403) | Read | Read | ❌ (Forbidden) |

---

## 3. Cryptographic Proposal Integrity (SHA-256)

To prevent price or quantity tampering between the time a draft proposal is reviewed and when it is approved, StockPilot AI generates a deterministic canonical SHA-256 hash:

$$\text{Canonical String} = \text{supplier}:\{\text{supplier\_id}\} \mid \text{items}:\{\text{product\_id}_1\}:\{\text{qty}_1\}:\{\text{cost}_1\},\dots$$

$$\text{Proposal Hash} = \text{SHA256}(\text{Canonical String})$$

When the manager clicks "Approve", the server recalculates the hash against live database pricing. If supplier prices or item quantities were altered, the transaction is immediately aborted with a `409 Conflict` error.

---

## 4. Prompt Injection Defense

StockPilot AI uses a defensive layering strategy:
- **System Prompt Isolation:** In [`prompts.py`](file:///i:/Projects/AI%20Projects/StockPilot%20AI/backend/app/agent/prompts.py), database records and user inputs are framed as raw untrusted data.
- **Immutable Guardrails:** The model is instructed that system guardrails and role boundaries cannot be overridden by user prompts (e.g. `"Ignore previous instructions"`, `"SYSTEM OVERRIDE"`, `"SuperAdmin"`).
- **Capability Isolation:** The AI environment does not possess any tool or API key able to call the `/approve` or `/purchase-orders` execution endpoints.

---

## 5. Log Sanitization & Correlation Tracing

- **Credential Redaction:** The logging system automatically scrubs API keys (`gsk_*`, `sk-*`), passwords, and authorization tokens before writing logs.
- **Correlation Request IDs:** Every HTTP request receives a unique `X-Request-ID` UUID4 header and is traced across application logs and audit records.
