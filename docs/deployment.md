# StockPilot AI — Deployment & Infrastructure Guide

## 1. Deployment Topology Overview

StockPilot AI supports two primary deployment modes:
1. **Local Containerized Deployment:** Full 3-tier local stack managed via Docker Compose for testing, evaluation, and developer demonstrations.
2. **Cloud Staging / Production Deployment:** Decoupled containerized backend and static Next.js frontend connected to managed PostgreSQL and Groq LLM Cloud.

---

## 2. Local Docker Compose Deployment

### Prerequisites
- Docker Engine 24+ and Docker Compose v2
- A free Groq Cloud API key (`gsk_...`)

### Quickstart
1. **Clone and create root `.env`:**
   ```bash
   cp .env.example .env
   # Edit .env and supply your GROQ_API_KEY
   ```

2. **Build and start services:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify running containers:**
   ```bash
   docker compose ps
   ```
   Expected output:
   - `stockpilot-postgres` (healthy on port 5432)
   - `stockpilot-backend` (healthy on port 8000)
   - `stockpilot-frontend` (running on port 3000)

4. **Access the application:**
   - Frontend Dashboard: [http://localhost:3000](http://localhost:3000)
   - Backend OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Backend Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

5. **Stop services:**
   ```bash
   docker compose down
   ```

---

## 3. Recommended Cloud Deployment Strategy

```mermaid
flowchart TD
    Client([Web Users & Mobile]) -->|HTTPS / SSL| VercelEdge[Next.js Frontend on Vercel / Cloudflare]
    VercelEdge -->|HTTPS API Requests| BackendContainer[FastAPI Backend on Render / Fly.io / Railway]
    
    BackendContainer -->|Encrypted SQL Session| ManagedPostgres[(Managed PostgreSQL 16 on Neon / Supabase)]
    BackendContainer -->|HTTPS API Requests| GroqCloud[Groq Cloud LLM API]
    
    subgraph Storage [Persistent Storage]
        ManagedPostgres
    end
```

### 3.1 Recommended Provider Selection
| Component | Recommended Provider | Alternative Options | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend API** | **Render / Fly.io** | Railway / AWS ECS | Native Dockerfile support, automatic HTTPS, healthchecks, secrets management. |
| **Frontend UI** | **Vercel** | Cloudflare Pages / Netlify | Optimal Next.js 15 App Router caching, global CDN edge network. |
| **Database** | **Neon / Supabase** | Render Postgres / AWS RDS | Managed PostgreSQL 16, connection pooling (PgBouncer), automated backups. |
| **LLM Inference** | **Groq Cloud API** | Ollama (Local Self-Hosted) | Ultra-fast token latency for tool-calling loops (`llama-3.3-70b-versatile`). |

---

## 4. Environment Variables Reference

### Backend Environment Variables
| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime environment mode | `production` / `development` |
| `DEBUG` | Enable debug logs | `false` |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `GROQ_API_KEY` | Groq Cloud API Authentication Key | `gsk_...` |
| `LLM_PROVIDER` | LLM backend adapter | `groq` |
| `LLM_MODEL_NAME` | Model identifier | `llama-3.3-70b-versatile` |
| `BACKEND_CORS_ORIGINS`| Allowed origin URLs | `["https://app.stockpilot.com"]` |

### Frontend Environment Variables
| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | Public URL to FastAPI API endpoint | `https://api.stockpilot.com/api/v1` |
| `PORT` | Listening web server port | `3000` |

---

## 5. Cost & Free-Tier Limitations Analysis

> [!WARNING]
> Free-tier hosting providers have real architectural constraints that impact production viability.

| Provider / Tier | Constraints & Limitations | Impact on StockPilot AI | Production Mitigation |
| :--- | :--- | :--- | :--- |
| **Render / Railway Free Tier** | Spins down after 15 minutes of inactivity; 50-second cold starts. | Initial chat queries experience high latency if spun down. | Upgrade to persistent instance (\$7/mo) for continuous uptime. |
| **Managed DB Free Tier (Neon/Supabase)** | Inactivity suspension, 0.5 GB storage limit, connection limits. | Database connection pool exhaustion during traffic spikes. | Enable PgBouncer connection pooler in asyncpg connection string. |
| **Groq Cloud Free Tier** | Rate limits: 30 requests/min, token quotas per day. | Multi-turn agent conversations may encounter rate-limit errors during bursts. | Implement backoff retries and request batching. |
| **Ephemeral Container Storage** | Local container disk is wiped on every deploy/restart. | Local SQLite or in-memory checkpoints are lost on restart. | **Always use external PostgreSQL** for both domain data and LangGraph checkpoints. |

---

## 6. Production Readiness Checklist

- [x] Docker multi-stage builds with non-root security users.
- [x] Health check endpoints implemented for all services.
- [x] CORS origins restricted to approved frontend domain.
- [x] Database migrations managed via version-controlled Alembic scripts.
- [x] Automated initial seeding script for reproducible deployments.
- [x] Sensitive credentials scrubbed from application logs.
- [x] Bounded retries on safe read tools; zero retries on mutating operations.
- [x] Cryptographic SHA-256 hash validation on all purchase approvals.
