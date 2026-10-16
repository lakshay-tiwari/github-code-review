# Cortex Architecture — Phase 1: Project Foundation & Local Infrastructure

This document describes the architectural baseline established in Phase 1 for the **Cortex** GitHub Codebase RAG application, following the [master-prompt.md](file:///media/lakshya-tiwari/DATA/Coding/cortex-2/ai-instructions/master-prompt.md) source of truth.

---

## 1. Directory Structure

```text
cortex-2/
├── web/                     # Next.js App Router frontend (TypeScript, Tailwind, pnpm)
│   ├── src/
│   │   └── app/
│   │       ├── layout.tsx
│   │       ├── page.tsx
│   │       └── globals.css
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── api/                     # FastAPI and shared Python application
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── router.py  # API routes & /health endpoint
│   │   ├── core/
│   │   │   └── config.py      # Pydantic Settings
│   │   ├── domain/            # Domain models (Phase 3+)
│   │   ├── services/          # Business logic services (Phase 3+)
│   │   ├── infrastructure/    # DB, vector & graph adapters (Phase 3+)
│   │   ├── workers/           # Celery worker definitions (Phase 3+)
│   │   └── main.py            # FastAPI entry point & CORS
│   ├── tests/
│   │   └── test_health.py     # Health endpoint verification
│   └── pyproject.toml         # Python package specification
├── infra/
│   └── docker-compose.yml   # PostgreSQL, Redis, Qdrant, Neo4j
├── docs/
│   └── architecture.md      # This document
├── .env.example             # Safe placeholder template for environment variables
├── .gitignore               # Multi-language Git ignore
└── README.md                # Quickstart & operational commands
```

---

## 2. Service Responsibilities

| Service | Technology | Responsibility | Host Port | Internal Container URL |
|---|---|---|---|---|
| **Frontend** (`web/`) | Next.js 16 App Router (React 19, Tailwind CSS) | Public landing, authenticated dashboard, chat UI, streamed responses, file citations. Proxies API requests. | `3000` | N/A (runs on host / Node) |
| **API Backend** (`api/`) | FastAPI, Uvicorn, Python 3.12+ | Handles REST APIs, response streaming, auth token validation, session management. | `8000` | `http://api:8000` |
| **Ingestion Worker** (`api/`) | Celery, Redis | Executes background ingestion: git clone, Tree-sitter parsing, embedding generation, Qdrant/Neo4j indexing. | N/A | Worker process |
| **PostgreSQL** | PostgreSQL 16 Alpine | Durable relational store for users, repositories, indexing jobs, conversations, messages. Owned by SQLAlchemy/Alembic. | `5432` | `postgresql+asyncpg://cortex:cortex_dev_password@postgres:5432/cortex` |
| **Redis** | Redis 7 Alpine | Asynchronous task queue broker and result store for Celery. | `6379` | `redis://redis:6379/0` |
| **Qdrant** | Qdrant v1.12.1 | Vector database storing code chunk embeddings with repository & commit SHA payload filtering. | `6333` (HTTP)<br>`6334` (gRPC) | `http://qdrant:6333` |
| **Neo4j** | Neo4j 5 Community | Code relationship graph storing imports, call hierarchies, class structures, and symbol links. | `7474` (HTTP)<br>`7687` (Bolt) | `bolt://neo4j:7687` |

---

## 3. High-Level Architecture Diagram

```mermaid
graph TD
    Client["User Browser"] -->|HTTPS / Port 3000| Web["Next.js Frontend (web/)"]
    Web -->|Internal Proxy / Port 8000| API["FastAPI Backend (api/)"]

    subgraph "Local Infrastructure (Docker Compose)"
        Postgres[("PostgreSQL 16\nPort 5432")]
        Redis[("Redis 7\nPort 6379")]
        Qdrant[("Qdrant Vector DB\nPort 6333")]
        Neo4j[("Neo4j Graph DB\nPort 7474 / 7687")]
    end

    API -->|SQLAlchemy / AsyncPG| Postgres
    API -->|RAG Vector Query| Qdrant
    API -->|Graph Query| Neo4j
    API -->|Enqueue Ingestion| Redis

    Worker["Celery Ingestion Worker"] -->|Poll Tasks| Redis
    Worker -->|Update Status| Postgres
    Worker -->|Upsert Vectors| Qdrant
    Worker -->|Upsert Code Graph| Neo4j
```

---

## 4. Host vs Container Networking

1. **Host-Run Commands (Local Development)**:
   - When running FastAPI (`uvicorn app.main:app`) or Next.js (`pnpm dev`) on the host machine, connections connect to `localhost:<port>`:
     - PostgreSQL: `localhost:5432`
     - Redis: `localhost:6379`
     - Qdrant: `http://localhost:6333`
     - Neo4j: `bolt://localhost:7687`
2. **Container-Run Services (Docker Network)**:
   - Within the Docker Compose bridge network (`cortex-network`), services resolve each other by container service name:
     - `postgres:5432`
     - `redis:6379`
     - `qdrant:6333`
     - `neo4j:7687`

---

## 5. Security & Isolation Principles

- **No Secrets in Source Control**: All credentials use `.env` files matching `.env.example`. Real secrets are strictly omitted from git.
- **Repository Isolation**: All vector and graph indexing records will be scoped by repository identifier and commit SHA to prevent cross-project leakage.
- **Isolated Package Boundaries**:
  - `web/` manages its own dependencies strictly with `pnpm`.
  - `api/` manages Python packages with `pyproject.toml` and an isolated virtual environment (`.venv/`).
  - No monorepo tools (Turborepo, root workspaces) to maintain clean separation.

---

## 6. Phase Roadmap Status

- **Phase 1 (Current)**: Project foundation, Next.js minimal shell, FastAPI health endpoint, Docker Compose infrastructure (Postgres, Redis, Qdrant, Neo4j).
- **Phase 2 (Upcoming)**: Frontend foundation and Clerk authentication shell.
- **Phase 3 (Subphases 3A–3F)**: Backend models, Clerk verification, LLM/embedding providers, Qdrant adapter, Neo4j adapter, Celery queue.
- **Phase 4**: Public repository submission & background ingestion pipeline.
- **Phase 5**: Tree-sitter syntax-aware code chunking & vector indexing.
- **Phase 6**: LangGraph RAG workflow, streaming, citations, history, checkpointing.
- **Phase 7**: Neo4j code graph, Mem0 memory, LangSmith tracing, guardrails & hardening.
