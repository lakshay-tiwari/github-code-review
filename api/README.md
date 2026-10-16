# Cortex API

FastAPI backend service and shared core package for the Cortex GitHub Codebase RAG system.

## Setup and Virtual Environment

This project uses a standard Python virtual environment inside `api/` with `pyproject.toml`.

### 1. Create and Activate Virtual Environment

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

### 3. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health` or `http://localhost:8000/api/v1/health`

### 4. Run Tests

```bash
pytest
```
