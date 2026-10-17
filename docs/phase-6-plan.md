# Phase 6 Implementation & Architecture: LangGraph RAG Chat, Checkpointing, Citations, & Streaming

## 1. Overview & Objectives
Phase 6 delivers the production codebase question-answering conversational pipeline for Cortex:
- **Conversation & Message Management**: Authenticated CRUD and message logging in PostgreSQL strictly isolated by verified Clerk subject ID.
- **LangGraph StateGraph Workflow**: Declarative RAG graph composed of discrete nodes:
  1. `retrieve_context`: Scoped semantic search over Qdrant code chunks filtered by `repository_id` and immutable `commit_sha`.
  2. `validate_evidence`: Evaluates retrieved chunks. If insufficient evidence is found, aborts LLM generation and directly states that no relevant evidence exists in the codebase.
  3. `generate_answer`: Prompts the configured LLM (`llama-3.3-70b-versatile` via Groq) with untrusted code context, strict citation rules (`[filepath#Lstart-Lend]`), and prompt-injection defenses.
- **Persistent LangGraph Checkpointing**: State persistence backed by `AsyncPostgresSaver` with connection pooling (`psycopg_pool.AsyncConnectionPool`) and auto-migration, with seamless `InMemorySaver` fallback for lightweight test environments.
- **Real-Time Token Streaming**: Server-Sent Events (SSE) streaming protocol via FastAPI `StreamingResponse` and Next.js proxy route, emitting structured events (`start`, `citations`, `chunk`, `done`, `error`).
- **Full Interactive Workspace UI**: Next.js Chat interface featuring repository selection, conversation threading, real-time token rendering, citation badges, and code copy tools.
- **No Celery in Chat Path**: Chat inference and streaming run entirely within asynchronous FastAPI request handlers, leaving Celery workers free for background ingestion.

---

## 2. Architecture & Graph Design

```mermaid
flowchart TD
    User([User Prompt]) --> NextProxy[Next.js API Proxy /api/conversations/[id]/messages]
    NextProxy --> FastAPIRoute[FastAPI POST /api/v1/conversations/{id}/messages]
    FastAPIRoute --> SaveUserMsg[(PostgreSQL: Save User Message)]
    SaveUserMsg --> StartGraph[LangGraph StateGraph START]
    StartGraph --> Retrieve[retrieve_context_node: Query Qdrant with Scoped Repository & Commit]
    Retrieve --> Validate[validate_evidence_node: Check Context & Grounding]
    Validate -->|Insufficient Evidence| EarlyExit[Emit Explanatory No-Evidence Message]
    Validate -->|Sufficient Evidence| Generate[generate_answer_node: Groq LLM astream with Grounded Prompt]
    Generate --> SSEStream[SSE Event Stream: start -> citations -> chunks -> done]
    EarlyExit --> SSEStream
    SSEStream --> SaveAsstMsg[(PostgreSQL: Save Assistant Message with Citations)]
    SaveAsstMsg --> Checkpoint[(LangGraph Checkpointer: AsyncPostgresSaver / InMemorySaver)]
    Checkpoint --> Browser([Browser UI: Real-time Markdown & Citation Badges])
```

---

## 3. Streaming Protocol Specification (SSE)

FastAPI emits standard `text/event-stream` payloads forwarded by the Next.js API route:

1. **`event: start`**
   ```json
   { "conversation_id": "...", "user_message_id": "...", "commit_sha": "..." }
   ```
2. **`event: citations`** (Emitted early so the UI can render reference cards immediately)
   ```json
   [
     {
       "file_path": "src/auth.py",
       "start_line": 15,
       "end_line": 42,
       "commit_sha": "abc1234...",
       "symbol_name": "authenticate_user",
       "snippet": "async def authenticate_user..."
     }
   ]
   ```
3. **`event: chunk`** (Emitted repeatedly as LLM yields tokens)
   ```
   data:  The function validates the RS256 JWT signature...
   ```
4. **`event: done`** (Emitted upon completion and DB commit)
   ```json
   { "message_id": "...", "conversation_id": "...", "status": "completed" }
   ```
5. **`event: error`** (Emitted if generation or network fails mid-stream)
   ```json
   { "error": "...", "partial": "..." }
   ```

---

## 4. Checkpointer Setup & Schema Ownership

- **Library**: `langgraph-checkpoint-postgres==3.2.0` with `psycopg_pool.AsyncConnectionPool` and `psycopg[binary]>=3.2.0`.
- **Connection Configuration**: Connects to PostgreSQL with `autocommit=True` (required for concurrent index migrations in `AsyncPostgresSaver.setup()`).
- **Tables Managed by LangGraph Checkpointer**:
  - `checkpoints`
  - `checkpoint_blobs`
  - `checkpoint_writes`
- **Ownership Separation**: LangGraph checkpoints preserve graph state snapshots for resuming multi-turn workflows; PostgreSQL `conversations` and `messages` tables remain the ground-truth relational entity store for user history and citations.

---

## 5. Verification Summary

- **Backend Pytest Suite**: 92 passed, 1 skipped (opt-in Groq live smoke test), 0 failed:
  - Evidence retrieval and citation formatting: PASSED
  - Insufficient evidence handling: PASSED
  - LangGraph checkpoint save/load and thread resumption: PASSED
  - PostgreSQL `AsyncPostgresSaver` live persistence: PASSED
  - Conversation CRUD and cross-user ownership isolation: PASSED
  - Full SSE streaming, citation emission, and message DB persistence: PASSED
- **Backend Linting**: `ruff check .` clean with 0 errors.
- **Frontend Type Safety**: `npx tsc --noEmit` clean with 0 errors.
- **Frontend Production Build**: `npm run build` completed with all routes statically optimized and dynamic proxies enabled.
- **Frontend Tests**: 17/17 passing in Vitest.
