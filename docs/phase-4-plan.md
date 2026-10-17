# Phase 4 — Repository Submission and Ingestion Jobs

## 1. Overview & Architecture

Phase 4 bridges user authentication (Phase 3B), database models (Phase 3A), background queue infrastructure (Phase 3F), and the Next.js frontend (Phase 2). It provides complete, verified server-side endpoints and asynchronous worker pipelines for submitting public GitHub repositories, validating resource constraints, and tracking ingestion job lifecycle states.

```
[Browser / UI] 
      │ (Clerk session token)
      ▼
[Next.js Server-Side Proxy] (`/api/repositories`, `/api/jobs/[id]`)
      │ (Bearer JWT forwarded to internal URL)
      ▼
[FastAPI Backend] (`/api/v1/repositories`, `/api/v1/jobs/[id]`)
      ├── 1. Cryptographic RS256 Clerk Verification -> UserContext
      ├── 2. Strict URL Validation & Reserved Path Filtering
      ├── 3. GitHub API Verification (Public access, Size <= 250MB, Commit SHA resolution)
      ├── 4. PostgreSQL Persistence (`repositories`, `ingestion_jobs`)
      └── 5. Celery Worker Enqueue -> Redis (`cortex_default` queue)
            │
            ▼
      [Celery Worker] (`index_repository_task`)
            ├── Step 1: Validating (`status: in_progress`, `progress: 15%`)
            ├── Step 2: Metadata Verified (`progress: 40%`)
            └── Step 3: Ready for Indexing (`current_step: ready_for_indexing`, `progress: 50%`)
                        (Actual chunking, embeddings, and graph extraction occur in Phase 5)
```

---

## 2. API Endpoints

All endpoints require verified Clerk Bearer tokens and enforce server-side ownership.

| Method | Path | Summary | Ownership / Scope |
|---|---|---|---|
| `POST` | `/api/v1/repositories` | Submit repository for indexing | Scoped to authenticated user (`owner_id`) |
| `GET` | `/api/v1/repositories` | List all repositories owned by user | Scoped to `current_user.user_id` |
| `GET` | `/api/v1/repositories/{id}` | Get repository details and latest job | `require_repository_ownership` |
| `POST` | `/api/v1/repositories/{id}/reindex` | Trigger background re-indexing job | `require_repository_ownership` |
| `DELETE` | `/api/v1/repositories/{id}` | Delete repository & purge vector/graph data | `require_repository_ownership` |
| `GET` | `/api/v1/jobs/{job_id}` | Check job progress, stage, and errors | `require_job_ownership` |

---

## 3. GitHub Validation & Guardrails

Implemented in [`api/app/services/github.py`](../api/app/services/github.py):

- **Regex Validation**: Only matches valid `https://github.com/{owner}/{repo}` paths. Rejects non-GitHub domains, internal IPs, credentials, or malformed path fragments.
- **Reserved Path Protection**: Explicitly blocks GitHub platform reserved keywords (`settings`, `explore`, `topics`, etc.).
- **Private Repository Rejection**: Only public repositories are accepted (`HTTP 400`).
- **Resource Limits**: Repositories exceeding `MAX_REPO_SIZE_MB` (default 250 MB) are rejected before cloning (`HTTP 422`).
- **Rate Limit Defense**: GitHub 403 Rate Limit errors are caught and surfaced safely as `HTTP 429` without leaking internals.
- **Commit Pinning**: Resolves the exact 40-character Git commit SHA from GitHub API on default branch, ensuring reproducible retrieval and citation grounding.

---

## 4. Execution Commands

- **Run FastAPI Backend**:
  ```bash
  cd api
  ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Run Celery Ingestion Worker**:
  ```bash
  cd api
  ./.venv/bin/celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q cortex_default
  ```
- **Run Next.js Web Frontend**:
  ```bash
  cd web
  npm run dev
  ```

---

## 5. Verification & Test Coverage

- **FastAPI Test Suite** (`pytest -v`):
  - **71 passed, 1 skipped** (opt-in Groq live test).
  - 12 comprehensive repository tests in [`api/tests/test_repositories.py`](../api/tests/test_repositories.py) covering URL validation, private repo rejection, size limit enforcement, 401 unauthorized, 403 cross-user access rejection, idempotent submissions, and Celery task execution.
- **Next.js Web Test Suite** (`npm test`):
  - **17 passed across 5 test suites**.
  - Includes Vitest tests for `/api/repositories` and `/api/auth/me` proxy routes.
- **Type Checking & Linting**:
  - `npx tsc --noEmit` in `web/`: 0 errors.
  - `ruff check .` in `api/`: 0 errors.
