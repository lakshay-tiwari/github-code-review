# Cortex — How to Run the Application

This guide contains the exact, step-by-step terminal commands to start all Cortex services locally.

---

## Architecture of Running Processes

To run the entire system, you need **4 components** running:

| Component | Location | Port / Protocol | Purpose |
| :--- | :--- | :--- | :--- |
| **1. Docker Containers** | `infra/` | `5432` (PG), `6379` (Redis), `6333` (Qdrant), `7687` (Neo4j) | Databases, vector store, and queue |
| **2. Celery Worker** | `api/` | Consumes from Redis | Clones repos, AST chunking, embeddings, and Neo4j indexing |
| **3. FastAPI Backend** | `api/` | `http://localhost:8000` | REST API, SSE chat streaming, auth validation |
| **4. Next.js Frontend** | `web/` | `http://localhost:3000` | User dashboard, repository manager, and chat UI |

---

## Terminal Commands (Step-by-Step)

Open **4 separate terminal windows or tabs**.

---

### Terminal 1: Start Docker Services

From the project root:

```bash
docker compose --project-directory . -f infra/docker-compose.yml up -d
```

To verify all 4 containers are healthy and running:
```bash
docker compose --project-directory . -f infra/docker-compose.yml ps
```

---

### Terminal 2: Celery Background Ingestion Worker

> **Important:** Always activate the virtual environment (`source .venv/bin/activate`) first, otherwise your shell will give `command not found: celery`.

```bash
cd /media/lakshya-tiwari/DATA/Coding/cortex-2/api

# 1. Activate Python virtual environment
source .venv/bin/activate

# 2. Run database migrations (only needed once or after schema updates)
alembic upgrade head

# 3. Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info -Q cortex_default
```

*(Alternative without activating venv: `./.venv/bin/celery -A app.workers.celery_app worker --loglevel=info -Q cortex_default`)*

---

### Terminal 3: FastAPI Backend API

```bash
cd /media/lakshya-tiwari/DATA/Coding/cortex-2/api

# 1. Activate Python virtual environment
source .venv/bin/activate

# 2. Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

*(Alternative without activating venv: `./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`)*

- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Terminal 4: Next.js Frontend

```bash
cd /media/lakshya-tiwari/DATA/Coding/cortex-2/web

# Start Next.js development server
npm run dev
```

The web application is now accessible at **[http://localhost:3000](http://localhost:3000)**.

---

## How to Use the Application

1. Open **[http://localhost:3000](http://localhost:3000)** in your browser.
2. Click **Sign In** or **Sign Up** (authenticates securely via Clerk).
3. Once logged in, you will be redirected to the **Dashboard** ([http://localhost:3000/dashboard](http://localhost:3000/dashboard)).
4. Click the purple **"+ Connect Repository"** button.
5. Paste any public GitHub repository URL, for example:
   ```text
   https://github.com/pallets/click
   ```
   *(No GitHub access token required for public repositories).*
6. Watch the real-time ingestion status change from `Queued` -> `Indexing` -> **`Ready`**.
7. In the left sidebar, click **Code Chat** ([http://localhost:3000/dashboard/chat](http://localhost:3000/dashboard/chat)).
8. Select your indexed repository from the dropdown menu and ask questions!
   - Cortex will perform hybrid vector and code graph retrieval.
   - Responses stream in real-time with verified line-number citations.

---

## Troubleshooting Common Issues

### 1. `zsh: command not found: celery` (or `uvicorn`)
- **Reason**: The Python virtual environment is not activated in that terminal.
- **Fix**: Run `source .venv/bin/activate` inside the `api` folder, or invoke the binary directly:
  ```bash
  ./.venv/bin/celery -A app.workers.celery_app worker --loglevel=info -Q cortex_default
  ```

### 2. `ERROR: [Errno 98] Address already in use`
- **Reason**: A previous `uvicorn` instance is still holding port `8000`.
- **Fix**: Free port 8000 and restart:
  ```bash
  fuser -k 8000/tcp 2>/dev/null || kill -9 $(lsof -t -i:8000) 2>/dev/null
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

### 3. Red "Unable to load repositories" on Dashboard
- **Reason**: FastAPI cannot verify the Clerk session token (usually missing keys or restrictive `CLERK_AUTHORIZED_PARTY`).
- **Fix**: Ensure `CLERK_AUTHORIZED_PARTY=` is empty in [`.env`](.env) and that [`.env`](.env) is copied to [`api/.env`](api/.env).

---

## Shutting Down

To stop the entire stack:
1. In Terminals 2, 3, and 4: Press `Ctrl + C`.
2. In Terminal 1 (or any terminal in the project root):
   ```bash
   docker compose --project-directory . -f infra/docker-compose.yml down
   ```
