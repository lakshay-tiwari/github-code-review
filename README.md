# Cortex — GitHub Codebase RAG Application

Cortex is a production-minded application that enables users to index public GitHub repositories and interact with codebases using Retrieval-Augmented Generation (RAG). It combines Tree-sitter syntax-aware code chunking, hybrid vector retrieval (Qdrant), relationship graphs (Neo4j), and LangGraph agentic workflows with strict line citations.

---

## Architecture Overview

```text
cortex-2/
├── web/                     # Next.js App Router frontend (TypeScript, Tailwind, pnpm)
├── api/                     # FastAPI backend and shared Python core package
├── infra/
│   └── docker-compose.yml   # PostgreSQL 16, Redis 7, Qdrant, Neo4j
├── docs/
│   └── architecture.md      # Detailed system architecture and networking guide
├── .env.example             # Environment variable template
├── .gitignore               # Multi-stack repository ignore rules
└── README.md                # Quickstart and run instructions
```

See [docs/architecture.md](docs/architecture.md) for detailed service responsibilities, host vs. container networking, and data flow diagrams.

---

## Prerequisites

- **Node.js**: >= 20.x
- **pnpm**: >= 9.x (isolated to `web/`)
- **Python**: >= 3.12
- **Docker & Docker Compose**: v2.20+

---

## Local Setup & Quickstart

### 1. Environment Configuration

Copy the template to create your local `.env`:

```bash
cp .env.example .env
```

### 2. Start Local Infrastructure

Start the background database and cache containers (PostgreSQL, Redis, Qdrant, Neo4j):

```bash
docker compose --project-directory . -f infra/docker-compose.yml up -d
```

Check service status and health checks:

```bash
docker compose --project-directory . -f infra/docker-compose.yml ps
```

Services exposed:
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **Qdrant**: `http://localhost:6333` (REST) / `localhost:6334` (gRPC)
- **Neo4j**: `http://localhost:7474` (Browser) / `bolt://localhost:7687`

### 3. Start FastAPI Backend

```bash
cd api

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package and development tools
pip install -e ".[dev]"

# Run FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/health` or `http://localhost:8000/api/v1/health`

### 4. Start Next.js Frontend

```bash
cd web

# Install dependencies (pnpm inside web/ only)
pnpm install

# Start Next.js dev server
pnpm dev
```

- Web App: `http://localhost:3000`

---

## Verification & Testing

### Python Backend Tests & Linting

```bash
cd api
source .venv/bin/activate

# Run tests
pytest

# Linting & Formatting
ruff check .
ruff format --check .
```

### Frontend Build & Linting

```bash
cd web

# Run production build
pnpm build

# Run linting
pnpm lint
```

### Infrastructure Health Check

```bash
docker compose --project-directory . -f infra/docker-compose.yml ps
```

---

## Phase Sequence Roadmap

1. **Phase 1** — Project foundation and local infrastructure. *(Completed)*
2. **Phase 2** — Frontend foundation and Clerk shell.
3. **Phase 3** — Backend foundations (Subphases 3A–3F: DB, Clerk Auth, Providers, Qdrant, Neo4j, Celery).
4. **Phase 4** — Repository submission and ingestion jobs.
5. **Phase 5** — Syntax-aware chunking, embeddings, and Qdrant indexing.
6. **Phase 6** — LangGraph RAG chat, streaming, citations, history, and checkpointing.
7. **Phase 7** — Neo4j graph, Mem0, LangSmith, guardrails, and hardening.
