# Phase 3 Subphases Plan — Backend Foundations and Adapters

This document establishes the architecture, dependencies, file paths, environment variables, verification criteria, and risk mitigations for Subphases 3A through 3F, in accordance with [master-prompt.md](../ai-instructions/master-prompt.md) and [phase-3_ba.md](../ai-instructions/phase-3_ba.md).

---

## Architecture Confirmation

- Strictly confined to: `web/`, `api/`, `infra/`, and `docs/`.
- **No Turborepo**, **no pnpm workspaces**, **no `apps/` directory**, and **no separate worker package**.
- Celery and FastAPI execute as independent processes importing the same unified Python package under `api/`.

---

## Subphase Breakdown

### Subphase 3A — PostgreSQL Models, SQLAlchemy, and Alembic

1. **Prerequisites & Dependencies**:
   - PostgreSQL 16 container running and healthy on host port `5432`.
   - Packages: `sqlalchemy[asyncio]>=2.0.36`, `asyncpg>=0.30.0`, `alembic>=1.14.0`, `psycopg2-binary>=2.9.10` (for sync Alembic runner if needed).
2. **Expected Files Under `api/`**:
   - `api/alembic.ini`
   - `api/alembic/env.py`
   - `api/alembic/script.py.mako`
   - `api/alembic/versions/` (initial migration)
   - `api/app/domain/models/base.py` (Base declarative class, timestamp mixin)
   - `api/app/domain/models/repository.py` (`Repository` model: owner Clerk ID, GitHub URL, default branch, commit SHA, status, timestamps)
   - `api/app/domain/models/job.py` (`IngestionJob` model: repo fk, status, progress, attempts, safe error, timestamps)
   - `api/app/domain/models/conversation.py` (`Conversation` model: repo fk, owner Clerk ID, title, timestamps)
   - `api/app/domain/models/message.py` (`Message` model: conversation fk, role, content, status, citations JSON, timestamps)
   - `api/app/infrastructure/db/session.py` (Async engine, `async_sessionmaker`, `get_db` session dependency)
   - `api/tests/test_database.py`
3. **Existing Code to Reuse**:
   - [`api/app/core/config.py`](../api/app/core/config.py): `settings.DATABASE_URL`, `settings.POSTGRES_*`.
   - [`infra/docker-compose.yml`](../infra/docker-compose.yml): Existing `postgres` service and volume.
4. **Required Environment Variables & Packages**:
   - `DATABASE_URL=postgresql+asyncpg://cortex:cortex_dev_password@localhost:5432/cortex`
   - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`
5. **Tests & Verification Criteria**:
   - Run Alembic migrations up to `head` against PostgreSQL.
   - Test async session lifecycle: create, read, commit, rollback on error, and verify foreign key cascading.
   - Verify index creation on `owner_id`, `github_url`, and foreign keys.
6. **Risks & Compatibility Questions**:
   - *Risk*: Alembic migration generator running against asyncpg URL.
   - *Mitigation*: Configure `alembic/env.py` to use `connectable = async_engine_from_config` via `asyncio.run()`.

---

### Subphase 3B — Clerk Token Verification and Authorization

1. **Prerequisites & Dependencies**:
   - Subphase 3A models (for verifying user ownership of repositories and conversations).
   - Packages: `pyjwt[crypto]>=2.9.0` or `cryptography>=43.0.0`, `httpx>=0.27.0`.
2. **Expected Files Under `api/`**:
   - `api/app/core/security.py` (JWKS caching, asymmetric RSA/ECDSA signature verification, claims validation: `sub`, `iss`, `azp`)
   - `api/app/api/deps.py` (`get_current_user`, `require_repository_ownership`, `require_conversation_ownership`)
   - `api/app/api/v1/endpoints/auth_test.py` (Protected test seam `/api/v1/auth/me`)
   - `api/tests/test_auth.py`
3. **Existing Code to Reuse**:
   - [`api/app/core/config.py`](../api/app/core/config.py): Extended with `CLERK_JWKS_URL`, `CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTY`.
   - [`web/src/middleware.ts`](../web/src/middleware.ts): Client token generation and forward via authorization headers.
4. **Required Environment Variables & Packages**:
   - `CLERK_ISSUER` (e.g. `https://stunning-bobcat-41.clerk.accounts.dev` or generic dev URL)
   - `CLERK_JWKS_URL` (optional override; default derived from issuer)
   - `CLERK_AUTHORIZED_PARTY` (optional validation)
5. **Tests & Verification Criteria**:
   - Unit tests with generated RSA key pairs testing valid tokens, expired tokens, tampered signatures, and missing headers (401/403).
   - Test ownership enforcement: User A cannot access User B's repositories or conversations.
6. **Risks & Compatibility Questions**:
   - *Risk*: Network calls to fetch Clerk JWKS on every request.
   - *Mitigation*: Cache JWKS public keys in-memory with a TTL and refresh on unknown `kid`.

---

### Subphase 3C — LLM and Embedding Provider Interfaces

1. **Prerequisites & Dependencies**:
   - Packages: `langchain-core>=0.3.0`, `langchain-groq>=0.2.0`, `sentence-transformers>=3.3.0` (or local embedding runtime).
2. **Expected Files Under `api/`**:
   - `api/app/infrastructure/llm/interfaces.py` (`BaseChatModel` abstract protocol: `agenerate`, `astream`)
   - `api/app/infrastructure/llm/groq_provider.py` (`GroqChatProvider` wrapping `ChatGroq`)
   - `api/app/infrastructure/llm/factory.py` (Central factory resolving provider by `settings.LLM_PROVIDER`)
   - `api/app/infrastructure/embeddings/interfaces.py` (`BaseEmbeddingProvider` abstract protocol: `embed_query`, `embed_documents`, `dimension`)
   - `api/app/infrastructure/embeddings/sentence_transformer.py` (`SentenceTransformerEmbeddingProvider`)
   - `api/app/infrastructure/embeddings/factory.py` (Central factory resolving embedding provider)
   - `api/tests/test_providers.py`
3. **Existing Code to Reuse**:
   - [`api/app/core/config.py`](../api/app/core/config.py): Extended with `LLM_PROVIDER`, `GROQ_API_KEY`, `GROQ_MODEL`, `EMBEDDING_MODEL`.
4. **Required Environment Variables & Packages**:
   - `LLM_PROVIDER=groq`, `GROQ_API_KEY=gsk_placeholder`, `GROQ_MODEL=llama-3.3-70b-versatile`
   - `EMBEDDING_PROVIDER=sentence-transformers`, `EMBEDDING_MODEL=all-MiniLM-L6-v2`
5. **Tests & Verification Criteria**:
   - Mocked unit tests for provider instantiation, interface compliance, error handling on missing keys.
   - Verification of vector dimension output (384 dimensions for MiniLM-L6-v2) exposed in provider metadata.
   - Zero paid or network API calls during standard test suites.
6. **Risks & Compatibility Questions**:
   - *Risk*: `sentence-transformers` loading heavy PyTorch dependencies during FastAPI startup.
   - *Mitigation*: Lazy initialization upon first usage; provider interface guarantees singleton instance reuse.

---

### Subphase 3D — Vector-Store Interface and Qdrant Adapter

1. **Prerequisites & Dependencies**:
   - Qdrant container running and healthy on host port `6333`/`6334`.
   - Subphase 3C embedding dimensions (384 for MiniLM-L6-v2).
   - Packages: `qdrant-client>=1.12.0`.
2. **Expected Files Under `api/`**:
   - `api/app/infrastructure/vector/interfaces.py` (`BaseVectorStore` protocol: `ensure_collection`, `upsert_chunks`, `search`, `delete_by_repository`)
   - `api/app/infrastructure/vector/qdrant_adapter.py` (`QdrantVectorStoreAdapter` with payload schema & index management)
   - `api/tests/test_qdrant.py`
3. **Existing Code to Reuse**:
   - [`api/app/core/config.py`](../api/app/core/config.py): `settings.QDRANT_URL`, `settings.QDRANT_HOST`, `settings.QDRANT_HTTP_PORT`.
   - [`infra/docker-compose.yml`](../infra/docker-compose.yml): Running `qdrant` container.
4. **Required Environment Variables & Packages**:
   - `QDRANT_URL=http://localhost:6333`, `QDRANT_COLLECTION_NAME=cortex_code_chunks`
5. **Tests & Verification Criteria**:
   - Mocked adapter tests for filter structure, search queries, and payload serialization.
   - Optional live integration test against local Qdrant container: collection creation, upsert chunk, query with `repository_id` and `commit_sha` filters, and scoped deletion.
6. **Risks & Compatibility Questions**:
   - *Risk*: Dimension mismatch between collection and embedding provider.
   - *Mitigation*: Adapter validates existing collection vector size at startup and raises an explicit `VectorDimensionMismatchError`.

---

### Subphase 3E — Graph-Store Interface and Neo4j Adapter

1. **Prerequisites & Dependencies**:
   - Neo4j 5 Community container running and healthy on host port `7474`/`7687`.
   - Packages: `neo4j>=5.26.0`.
2. **Expected Files Under `api/`**:
   - `api/app/infrastructure/graph/interfaces.py` (`BaseGraphStore` protocol: `upsert_nodes`, `upsert_relationships`, `get_neighbors`, `delete_repository`)
   - `api/app/infrastructure/graph/neo4j_adapter.py` (`Neo4jGraphStoreAdapter` with parameterized Cypher queries)
   - `api/tests/test_neo4j.py`
3. **Existing Code to Reuse**:
   - [`api/app/core/config.py`](../api/app/core/config.py): `settings.NEO4J_URI`, `settings.NEO4J_USER`, `settings.NEO4J_PASSWORD`.
   - [`infra/docker-compose.yml`](../infra/docker-compose.yml): Running `neo4j` container.
4. **Required Environment Variables & Packages**:
   - `NEO4J_URI=bolt://localhost:7687`, `NEO4J_USER=neo4j`, `NEO4J_PASSWORD=cortex_dev_password`
5. **Tests & Verification Criteria**:
   - Mocked driver tests ensuring all queries use parameterized Cypher (no string concatenation).
   - Scoped queries verify filtering by `repository_id` and `commit_sha`.
   - Integration test with running Neo4j container verifying session management and constraint creation.
6. **Risks & Compatibility Questions**:
   - *Risk*: Connection leaks if driver sessions are not closed properly in async tasks.
   - *Mitigation*: Manage driver lifecycle via async context managers (`AsyncGraphDatabase.driver`).

---

### Subphase 3F — Celery and Redis Queue Foundation

1. **Prerequisites & Dependencies**:
   - Redis 7 container running and healthy on host port `6379`.
   - Subphase 3A models (for durable job updates).
   - Packages: `celery>=5.4.0`, `redis>=5.2.0`.
2. **Expected Files Under `api/`**:
   - `api/app/workers/celery_app.py` (Celery application instance, task autodiscovery, JSON serialization, broker URL)
   - `api/app/workers/tasks.py` (Smoke task `ping_task`, task base classes with error logging)
   - `api/tests/test_workers.py`
3. **Existing Code to Reuse**:
   - [`api/app/core/config.py`](../api/app/core/config.py): `settings.REDIS_URL`.
   - [`infra/docker-compose.yml`](../infra/docker-compose.yml): Running `redis` container.
4. **Required Environment Variables & Packages**:
   - `REDIS_URL=redis://localhost:6379/0`, `CELERY_BROKER_URL=redis://localhost:6379/0`
5. **Tests & Verification Criteria**:
   - Test task registration and importability in standalone worker mode (`celery -A app.workers.celery_app inspect registered`).
   - Test smoke task execution locally and verify result.
   - Verify Redis is not used as the durable application database (PostgreSQL owns job records).
6. **Risks & Compatibility Questions**:
   - *Risk*: Code duplication between FastAPI and Celery.
   - *Mitigation*: Celery worker imports the exact same `app.*` package modules, database models, and adapters as FastAPI.
