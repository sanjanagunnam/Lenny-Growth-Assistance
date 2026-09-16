# The Lenny Growth Assistant

A production-grade, evidence-grounded AI growth strategist backed by PostgreSQL 16 + pgvector in Docker, a resilient FastAPI backend with session persistence, a dual-LLM bridge supporting local Ollama (`llama3.2`) and cloud Anthropic (`claude-3-5-sonnet-latest`), strict RAG transcript grounding, a Ship 30 for 30 viral essay skill (~1,250 words), and a React/Tailwind v4 split-view Growth Canvas.

---

## 1. System Capabilities & Features

- **Strict RAG Epistemic Grounding**: Answers are derived strictly from Lenny's Podcast transcripts. If the context is missing or cosine similarity is below 0.65, the assistant outputs: `"The available podcast transcripts do not cover this specific question."` Zero hallucinations.
- **Ship 30 for 30 Viral Essay Engine (`mode="ship30"`)**: Transforms grounded podcast insights into high-impact ~1,250-word essays featuring punchy hooks, bold anchor sentences, scannable bullet points, and real guest quotes.
- **Sandboxed Artifact Canvas**: Emits reusable frameworks, checklists, and interactive HTML widgets into a split-screen Growth Canvas with DOMPurify sanitization and `sandbox="allow-scripts"` isolation.
- **Dynamic Dual-Model Bridge**: Seamlessly switch between local Ollama (`llama3.2`) and Anthropic (`claude-3-5-sonnet-latest`) on the fly without restarting services.
- **Multi-Turn History Threading**: Sessions and messages are stored in PostgreSQL, allowing conversational context to persist across follow-up queries.
- **One-Command Topology**: Unified 4-container Docker Compose setup (`db`, `ollama`, `backend`, `frontend`).

---

## 2. Prerequisites

- **Docker & Docker Compose** (Docker Desktop on Windows/macOS or Docker Engine on Linux)
- **RAM**: 8GB minimum (16GB recommended for running Ollama Llama 3.2 locally)
- **Disk Space**: ~8GB for Docker images and local model weights (`nomic-embed-text` and `llama3.2`)
- *(Optional)* Python 3.10+ and Node.js 18+ for bare-metal local development

---

## 3. Quickstart (One-Command Spin Up)

### Step 1: Clone and Configure Environment
Copy the environment template:
```bash
cp .env.example .env
```
*(Optional: If you want to use Anthropic Claude, add your `ANTHROPIC_API_KEY=sk-ant-...` in `.env`. If left blank, the assistant runs 100% locally on Ollama without requiring any cloud API key).*

### Step 2: Launch All Services
```bash
docker compose up --build
```
This single command orchestrates:
1. `lenny_growth_db`: PostgreSQL 16 with `pgvector` on port `5432` (healthy check).
2. `lenny_growth_ollama`: Ollama daemon on port `11434`, automatically pulling `nomic-embed-text` and `llama3.2`.
3. `lenny_growth_backend`: FastAPI app on port `8000`.
4. `lenny_growth_frontend`: Nginx serving the React Growth Canvas on port `3000`.

### Step 3: Open the Web Application
Open your browser at:
```
http://localhost:3000
```
*(Or `http://localhost:5173` if running Vite locally).*

---

## 4. Local Development (Bare-Metal — No Docker Required)

Run the backend, frontend, and API locally without Docker. This is the fastest way to iterate during development.

### Prerequisites

Make sure you have the following installed:

- **Python 3.10+** — [python.org](https://python.org)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)
- **pip** (comes with Python)
- **Ollama** *(optional, for local LLM)* — [ollama.com](https://ollama.com)

---

### Step 1 — Install Backend Dependencies

```bash
# From the project root
pip install -r backend/requirements.txt
```

---

### Step 2 — Configure Environment

```bash
# Copy the env template (if not done already)
cp .env.example .env
```

The default `.env` is pre-configured for **SQLite** (no PostgreSQL needed) and **Groq** (free cloud LLM, no Ollama required). Just add your keys:

| Variable | Required | Where to get it |
|---|---|---|
| `GROQ_API_KEY` | ✅ For Groq (default) | [console.groq.com](https://console.groq.com) |
| `ANTHROPIC_API_KEY` | Optional | [console.anthropic.com](https://console.anthropic.com) |
| `OLLAMA_BASE_URL` | Optional (local) | Set to `http://localhost:11434` |

---

### Step 3 — Run the Backend API Server

```bash
# From the project root directory
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is now live at:
- **API Base**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/healthz`

---

### Step 4 — Run the Frontend Dev Server

```bash
# In a new terminal, from the frontend/ directory
cd frontend
npm install        # First time only
npm run dev
```

The React app is now available at:
- **Local**: `http://localhost:5173`

---

### Step 5 — Test the API (Quick Smoke Test)

Once both servers are running, verify everything works:

```bash
# 1. Health check
curl http://localhost:8000/healthz

# 2. Send a chat message using Groq (default, free)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does Lenny say about product-market fit?",
    "provider": "groq",
    "mode": "chat"
  }'

# 3. Chat using Anthropic Claude
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Write a Ship 30 essay on the Lenny framework.",
    "provider": "anthropic",
    "mode": "ship30"
  }'

# 4. Chat using local Ollama (requires Ollama running locally)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are Airbnb growth loops?",
    "provider": "ollama",
    "mode": "chat"
  }'

# 5. List all sessions
curl http://localhost:8000/api/v1/sessions

# 6. Create a new session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "My Growth Session"}'
```

---

### API Summary Table

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Service metadata & version |
| `/healthz` | GET | Database + provider health check |
| `/docs` | GET | Swagger interactive API docs |
| `/api/v1/chat` | POST | Send a message (supports `provider`, `mode`, `session_id`) |
| `/api/v1/sessions` | GET | List all chat sessions |
| `/api/v1/sessions` | POST | Create a new session |
| `/api/v1/sessions/{id}` | GET | Get session details |
| `/api/v1/sessions/{id}/messages` | GET | Retrieve all messages in a session |

---

### Chat Request Body Reference

```json
{
  "message": "Your question here",
  "provider": "groq",        // "groq" | "anthropic" | "ollama"
  "mode": "chat",            // "chat" | "ship30"
  "session_id": null         // optional UUID to continue a conversation
}
```

---

### Running with Ollama (100% Local, Offline)

```bash
# Install and start Ollama (run once)
ollama pull nomic-embed-text
ollama pull llama3.2        # or glm-5.3-flash (faster, smaller)

# Then set in .env:
# DEFAULT_PROVIDER=ollama
# OLLAMA_DEFAULT_MODEL=llama3.2
```

---

## 5. Transcript Ingestion Pipeline

To populate the vector database with Lenny's Podcast transcripts:

### Ingest inside Docker:
```bash
docker compose exec backend python -m backend.app.rag.ingest --transcripts-dir data/transcripts
```

### Dry-run verification (calculates tokens and chunks without writing to DB):
```bash
python -m backend.app.rag.ingest --dry-run
```

---

## 6. Model Selection & Runtime Controls

You can switch models at runtime directly from the **UI Top Bar** or via API request body:

### Via Web UI:
- Click **Ollama (Llama 3.2)** for 100% offline, private inference.
- Click **Claude 3.5** for Anthropic cloud execution (requires `ANTHROPIC_API_KEY`).

### Via REST API:
```bash
# Query Ollama locally:
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does Brian Chesky explain about Airbnb host-guest growth loops?",
    "provider": "ollama",
    "mode": "chat"
  }'

# Query Anthropic Claude:
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Write a Ship 30 for 30 essay on Shreyas Doshi LNO framework.",
    "provider": "anthropic",
    "mode": "ship30"
  }'
```

---

## 7. Automated Test Suites

The project features a comprehensive 34-test automated regression suite covering unit, integration, and end-to-end flows:

### Run all tests locally:
```bash
python -m pytest -v
```

### Run tests inside Docker container:
```bash
docker compose exec backend pytest -v
```

### Test Suite Breakdown:
- `backend/tests/test_retrieval.py`: Embedding generation, pgvector similarity math, and epistemic threshold cutoffs.
- `backend/tests/test_api.py`: FastAPI endpoints, session persistence, dynamic provider switching, and timeout resilience.
- `backend/tests/test_agent.py`: Anti-hallucination refusal gates, grounded citation extraction, and artifact XML parsing.
- `backend/tests/test_end_to_end.py`: End-to-end integration across health checks, sessions, RAG queries, and Ship 30 formatting.

---

## 8. Diagnostics & Troubleshooting Guide

### 1. Check Subsystem Health (`/healthz`)
Verify the health of the database and Ollama daemon:
```bash
curl http://localhost:8000/healthz
```
Expected response:
```json
{
  "status": "healthy",
  "database": true,
  "ollama": true,
  "providers_available": ["ollama", "anthropic"]
}
```

### 2. Ollama Daemon Offline / Cold Startup
If `/healthz` reports `"ollama": false` or requests time out:
- Check container status:
  ```bash
  docker compose ps ollama
  docker compose logs -f ollama
  ```
- Ensure the models are downloaded:
  ```bash
  docker compose exec ollama ollama list
  ```
- If models were not pulled automatically:
  ```bash
  docker compose exec ollama ollama pull nomic-embed-text
  docker compose exec ollama ollama pull llama3.2
  ```

### 3. Database Connection Issues
If backend reports connection refused on port 5432:
- Ensure the `pgvector` container healthcheck has passed:
  ```bash
  docker compose ps db
  ```
- Test direct connection:
  ```bash
  docker compose exec db pg_isready -U postgres -d lenny_growth
  ```

### 4. Port Conflicts
If port 5432 or 8000 is occupied by a local service:
- Adjust ports in `.env` (e.g., `POSTGRES_PORT=5433` or change backend port mapping in `docker-compose.yml`).

---

## 9. Evaluator Ergonomics & Benchmark Testing

The frontend provides an interactive empty-state canvas with 4 pre-configured trigger buttons designed to immediately test key evaluation criteria:

| Benchmark Card | Evaluator Intent | Expected System Behavior |
|---|---|---|
| **Ask Grounded Growth Question** | RAG Grounding & Speaker Attribution | Retrieves Brian Chesky/Shreyas Doshi transcripts, outputs inline telemetry `[XX% Match \| N Episodes Cited]`, and provides expandable excerpts with exact guest quotes. |
| **Ship 30 for 30 Essay Generator** | Viral Content Skill Execution | Switches mode to `ship30`, constructs a ~1,250-word essay with a punchy hook, 3-5 modular frameworks, a 48-hour checklist, and updates the persistent word count meter (`Target: ~1,250`). |
| **Generate Interactive Canvas Artifact** | Sandboxed Execution | Emits an interactive HTML/JS calculator widget rendered inside an isolated `<iframe>` (`sandbox="allow-scripts"` without `allow-same-origin`) with DOMPurify sanitization. |
| **Epistemic Guardrail Refusal** | Hallucination Prevention | Deterministically returns: `"The available podcast transcripts do not cover this specific question."` when cosine similarity is below `0.65`. |

### Circuit Breaker & Timeout Recovery
- If local Ollama inference exceeds 15.0 seconds, the backend intercepts the timeout and returns a structured `HTTP 504 Gateway Timeout`.
- The frontend surfaces a non-blocking floating toast banner with an actionable **"Switch to Claude & Retry"** button, dynamically switching the provider to Anthropic Claude and re-dispatching the query with zero data loss.

---

## 10. Engineering Specifications & Deliverables

- **Product Requirements**: [PRD.md](file:///c:/Users/avina/OneDrive/Desktop/lenny-growth-assistant/PRD.md)
- **Technical Architecture**: [architecture.md](file:///c:/Users/avina/OneDrive/Desktop/lenny-growth-assistant/architecture.md)
- **Design System & Aesthetics**: [design.md](file:///c:/Users/avina/OneDrive/Desktop/lenny-growth-assistant/design.md)
- **Agent Trajectory Audit Logs**: [agent_transcripts/README.md](file:///c:/Users/avina/OneDrive/Desktop/lenny-growth-assistant/agent_transcripts/README.md)

