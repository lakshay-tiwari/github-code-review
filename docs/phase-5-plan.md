# Phase 5 Implementation Plan & Architecture: Syntax-Aware Chunking, Embeddings, & Qdrant

## 1. Overview & Objectives
Phase 5 establishes the syntactic parsing, vectorization, and dense semantic search infrastructure for Cortex:
- Download GitHub repository archive at the exact immutable commit SHA.
- Cleanly filter out binary files, dependency paths (`node_modules`, `.venv`, `.git`), build artifacts, lockfiles, and secrets.
- Syntax-aware AST chunking with Tree-sitter for structured code units (functions, classes, methods) with fallback sliding windows.
- Deterministic chunk identity via UUIDv5 (`dns` namespace + `repo_id:file_path:start_line:end_line`).
- Normalized dense embeddings generated using the configured embedding provider (`all-MiniLM-L6-v2`, 384 dimensions).
- Scalable, batch upsert into Qdrant vector collections scoped by repository and user ownership.
- Direct semantic search endpoint (`POST /api/v1/repositories/{id}/search`) protected by Clerk RS256 token verification.

---

## 2. Pipeline Components

### 2.1 File Filtering (`app/services/file_filter.py`)
- **Excluded Directories**: `.git`, `node_modules`, `dist`, `build`, `.next`, `.venv`, `venv`, `__pycache__`, `.idea`, `.vscode`, `target`, `bin`, `obj`.
- **Excluded Extensions & Lockfiles**:
  - Lockfiles: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`, `Cargo.lock`, `Pipfile.lock`.
  - Media & binaries: `.png`, `.jpg`, `.jpeg`, `.gif`, `.ico`, `.svg`, `.mp4`, `.zip`, `.tar`, `.gz`, `.pdf`, `.pyc`, `.wasm`, `.dylib`, `.so`, `.dll`.
- **Secret & Sensitive File Defense**:
  - Rejects `.env`, `.env.*`, `*.pem`, `*.key`, `id_rsa`, `id_ed25519`, `credentials.json`.
- **File Size Safety**: Excludes files greater than 1 MB (1,048,576 bytes) or with null-byte binary headers.

### 2.2 Archive Extraction (`app/services/cloner.py`)
- Downloads repository tarball via `api.github.com/repos/{owner}/{repo}/tarball/{commit_sha}` using streaming response.
- Safe tar extraction utilizing Python 3.12's `tarfile.data_filter` to defend against:
  - Directory traversal (`../`).
  - Absolute path hijacking.
  - Dangerous symlinks and hardlinks.
  - Suspicious device file entries.

### 2.3 Syntax-Aware Chunking (`app/services/chunker.py`)
- Tree-sitter AST parsing using `tree-sitter==0.21.3` and `tree-sitter-languages>=1.10.0`.
- Supported grammar mappings:
  - Python: `function_definition`, `class_definition`, `async_function_definition`.
  - TypeScript / TSX: `function_declaration`, `class_declaration`, `method_definition`, `interface_declaration`, `type_alias_declaration`.
  - JavaScript / JSX: `function_declaration`, `class_declaration`, `method_definition`.
  - Go, Rust, Java, C, C++: structural declarations.
- Accurate line indexing: exact 1-indexed `start_line` and `end_line` derived from AST node byte offsets.
- Window chunker fallback: For unsupported languages (e.g. Markdown, plain text, config files) or oversized AST nodes, segments lines into overlapping sliding windows (default 50 lines with 10 lines overlap).
- Deterministic chunk ID:
  ```python
  uuid.uuid5(uuid.NAMESPACE_DNS, f"{repository_id}:{file_path}:{start_line}:{end_line}")
  ```

### 2.4 Indexer & Vector Store (`app/services/indexer.py` & `app/infrastructure/vector`)
- Batched embedding generation (default batch size: 64 chunks) via `BaseEmbeddingProvider.embed_documents`.
- Batched upsert to Qdrant collection `code_chunks` using `QdrantVectorStoreAdapter.upsert_chunks`.
- Payload Schema:
  - `chunk_id`: UUID
  - `repository_id`: UUID
  - `file_path`: String
  - `start_line`: Integer
  - `end_line`: Integer
  - `symbol_name`: Optional[String]
  - `language`: String
  - `content`: String
  - `content_hash`: SHA256 hex string

### 2.5 Semantic Search & Retrieval (`app/services/retrieval.py`)
- Query vectorization using `BaseEmbeddingProvider.embed_query(query)`.
- Filtered vector similarity search in Qdrant scoped to `repository_id`.
- Threshold filtering and top-k ranking.
- REST Endpoint: `POST /api/v1/repositories/{id}/search`
  - Validates repository existence and user ownership via Clerk JWT.
  - Returns array of scored chunk matches with symbol metadata and code snippets.
- Next.js proxy route: `POST /api/repositories/[id]/search`.

---

## 3. Celery Ingestion Job Workflow
1. **0% - 15%**: Validates repository metadata and commit SHA from GitHub.
2. **15% - 40%**: Downloads and safely unpacks repository archive into temporary directory.
3. **40% - 60%**: Filters files and parses syntax-aware code chunks.
4. **60% - 75%**: Enqueues chunks for vectorization.
5. **75% - 95%**: Batches embedding model inference and upserts vectors into Qdrant.
6. **95% - 100%**: Updates repository status to `ready` and ingestion job to `completed`.
