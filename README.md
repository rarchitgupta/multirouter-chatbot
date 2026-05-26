# Multi-router Chatbot

A multi-provider chatbot with real-time inference logging, an async ingestion pipeline, and an observability dashboard.

## What's here

- **Chatbot** — multi-turn streaming chat across Anthropic, OpenAI, and Gemini (via LiteLLM)
- **SDK wrapper** — captures latency, token usage, timestamps, and previews on every LLM call
- **Ingestion pipeline** — Redis Streams → background consumer → PostgreSQL, at-least-once delivery
- **PII redaction** — presidio-analyzer on log previews before they hit the DB; regex fallback if the spaCy model isn't installed
- **Dashboard** — P50/P90/P99 latency, request throughput, and error breakdown by provider

## Setup

```bash
cp .env.example .env
# add at least one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
```

### One command (Docker)

```bash
docker compose up --build
```

- Chat: http://localhost:3000
- Dashboard: http://localhost:3000/dashboard
- API docs: http://localhost:8000/docs

Migrations run automatically on backend startup.

### Kubernetes (self-hosted)

Manifests live in [k8s/](k8s/). Requires an nginx ingress controller.

**1. Build and push images**

```bash
docker build -t your-registry/llm-logger-api:latest .
docker build \
  --build-arg NEXT_PUBLIC_API_URL=http://api.example.com \
  -t your-registry/llm-logger-web:latest ./client
docker push your-registry/llm-logger-api:latest
docker push your-registry/llm-logger-web:latest
```

**2. Configure**

Edit [k8s/api.yaml](k8s/api.yaml) — fill in your image names and API keys in the `api-keys` Secret. Edit [k8s/ingress.yaml](k8s/ingress.yaml) — replace `example.com` with your domain (or `/etc/hosts` entries for local clusters). Update `CORS_ORIGINS` in the `api-config` ConfigMap to match your frontend domain.

**3. Apply**

```bash
kubectl apply -k k8s/
```

Migrations run automatically on API pod startup. The `/ready` probe waits for the database before traffic is routed.

### Local dev

You'll need [uv](https://docs.astral.sh/uv/) and [bun](https://bun.sh).

```bash
# Terminal 1 — infrastructure only
docker compose up postgres redis

# Terminal 2 — backend
uv run alembic upgrade head   # first time only
uv run fastapi dev app/main.py

# Terminal 3 — frontend
cd client && bun dev
```

## Architecture

```
Next.js frontend
      │ REST + SSE
FastAPI backend
  ├── LLM Wrapper (LiteLLM) ──XADD──▶ Redis Stream
  ├── Conversation CRUD                      │
  └── Analytics API              background consumer
                                       │ validate + redact
                                  PostgreSQL
                          conversations / messages / inference_logs
```

The logging path is fully off the critical path: after streaming finishes, the wrapper does one `XADD` and returns. The consumer processes asynchronously. Failed messages stay in the Redis PEL and are retried after 30s via `XAUTOCLAIM`.

## Schema

Three tables. `conversations` and `messages` are straightforward. `inference_logs` is the interesting one:

- Separate from `messages` so analytics queries never need to join on message content
- `input_preview` / `output_preview` store the first 200 chars, PII-redacted — fast for dashboards without loading full content
- `raw_metadata JSONB` absorbs provider-specific fields without schema migrations
- Indexed on `(provider, model, request_at)` and `(status, request_at)` for the dashboard queries

Conversations are soft-deleted via `status = 'cancelled'` rather than hard deletes, to preserve the log history.

## Tradeoffs

**Redis Streams over a direct DB write** — adds an operational dependency but fully decouples the ingestion latency from the chat response. A logging failure never affects the user.

**Consumer runs in the same process as the API** — simpler to deploy (one thing to run), uses the same DB pool. A dedicated worker process would better isolate slowdowns.

**`messages.content` isn't redacted** — only the previews in `inference_logs` are. Good enough for a prototype; production would need encryption at rest or field-level redaction.

**No auth** — the API is wide open. Wouldn't ship this without at least API key middleware on the backend.

## What I'd improve

- Idempotent ingestion — add a `request_id` so retries don't create duplicate rows
- Auth
- Tests
- Grafana + Prometheus for deeper infra-level metrics alongside the SQL dashboard
