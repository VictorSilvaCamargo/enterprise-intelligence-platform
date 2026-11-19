# Setup, Execution, and Verification Guide

This guide describes how to configure, run, and verify the **Stage 1** foundation of the Enterprise Intelligence Platform on **Windows (PowerShell / Docker Desktop)** and **Linux / macOS (Bash)**.

---

## 1. Prerequisites

| Tool | Verified Version | Purpose |
|---|---|---|
| **Docker & Docker Compose** | Docker `29.7.2` / Compose `v5.5.1` | Runs PostgreSQL, Redis, FastAPI backend, and Nginx frontend |
| **Git** | `2.55.0` | Version control (LF line endings managed by `.gitattributes`) |
| **Python** *(optional for host dev)* | `3.12.10` | Running backend tests, `ruff`, `mypy`, or local Uvicorn |
| **Node.js & npm** *(optional for host dev)* | Node `26.7.0` / npm `12.2.1` (Node `>=20.19` supported) | Running frontend lint, tests, Vite dev server, or builds |

---

## 2. Environment Configuration

Copy the documented template to `.env` (`.env` is gitignored and must never be committed):

**Windows PowerShell:**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS Bash:**
```bash
cp .env.example .env
```

Adjust ports or passwords in `.env` if needed. Inside Docker Compose, `backend` automatically resolves `POSTGRES_HOST=postgres` and `REDIS_HOST=redis` over the internal `eip_internal` network.

---

## 3. Running the Full Stack with Docker Compose (Recommended)

### Start all services
```powershell
docker compose up -d --build
```

### Monitor startup and health status
```powershell
docker compose ps
docker compose logs -f --tail=50
```

Wait until all four containers show **`(healthy)`**:
- `eip-postgres` (`postgres:17-alpine`, port `${POSTGRES_PORT:-5432}`)
- `eip-redis` (`redis:7-alpine`, port `${REDIS_PORT:-6379}`)
- `eip-backend` (FastAPI + Uvicorn, port `${BACKEND_PORT:-8000}`)
- `eip-frontend` (Nginx serving built React/Vite bundle, port `${FRONTEND_PORT:-5173}`)

### Access endpoints
- **Frontend Web App:** [http://localhost:5173](http://localhost:5173)
- **Backend Liveness:** [http://localhost:8000/health](http://localhost:8000/health)
- **Backend Readiness:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)
- **Swagger OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Run the automated stack verification script
**Windows PowerShell:**
```powershell
.\scripts\verify-stack.ps1
```

**Linux / macOS Bash:**
```bash
./scripts/verify-stack.sh
```

### Stop containers (preserving data volumes)
```powershell
docker compose down
```

> Avoid passing `-v` unless you intentionally want to wipe `eip_postgres_data` and `eip_redis_data`.

---

## 4. Running Without Full Containers (Local Host Development)

You can run Postgres and Redis in Docker while running Backend and Frontend directly on your host for fast hot-reload iteration:

1. Start only infrastructure services:
   ```powershell
   docker compose up -d postgres redis
   ```
2. Set `POSTGRES_HOST=localhost` and `REDIS_HOST=localhost` in `.env` (or export them in your shell).
3. Start the Backend API:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
4. In a second terminal, start the Frontend dev server:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

---

## 5. Running Code Quality & Automated Tests

### Backend (`backend/`)
```powershell
cd backend
.\.venv\Scripts\ruff.exe check app tests
.\.venv\Scripts\ruff.exe format --check app tests
.\.venv\Scripts\mypy.exe app
.\.venv\Scripts\pytest.exe -v
```

### Frontend (`frontend/`)
```powershell
cd frontend
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

---

## 6. Windows & Docker Troubleshooting

- **Line endings (CRLF vs LF):** `.gitattributes` enforces `LF` for Python, TypeScript, shell scripts, SQL, and Dockerfiles. If you cloned before `.gitattributes` took effect, run `git add --renormalize .`.
- **Port conflicts (`5173`, `8000`, `5432`, `6379`):** Change `FRONTEND_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`, or `REDIS_PORT` in `.env` and rebuild the frontend if `BACKEND_PORT` changes (`VITE_API_BASE_URL`).
- **Docker Desktop WSL2 slow bind-mounts:** Source builds run inside container filesystems rather than live host mounts in Stage 1 (`frontend/Dockerfile` builds static assets into Nginx; `backend/Dockerfile` copies `app/`), avoiding Windows-to-WSL2 I/O bottlenecks.
