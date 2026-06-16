# Shrine-Codex

Portable, service-split Docker version of the Vietnamese legal RAG chatbot.

## Services

- `api` - public FastAPI gateway on port `8000`
- `ingestion` - DOCX parsing/chunking/vector writing service on port `8003`
- `embedding` - sentence-transformers embedding service on port `8001`
- `reranker` - CrossEncoder reranker service on port `8002`
- `frontend` - Vite build served by Nginx on port `8080`
- `postgres`, `qdrant`, `redis` - persistent infra

## Run

```bash
cp .env.example .env
# Fill OPENAI_API_KEY, then:
docker compose up -d --build
```

The local `.env` can override host ports with:

```env
API_PORT_HOST=8000
FRONTEND_PORT_HOST=8080
POSTGRES_PORT_HOST=5432
QDRANT_PORT_HOST=6333
REDIS_PORT_HOST=6379
```

The app uses Docker-internal service DNS, so host-port overrides do not affect service-to-service calls.

## Verify

```bash
curl http://localhost:8000/api/health
curl -F "file=@sample.docx" http://localhost:8000/api/upload
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Thư viện xã có những nhiệm vụ gì và ai có trách nhiệm quản lý?"}'
```

Alembic runs from `scripts/entrypoint.sh` before `api` and `ingestion` start. The baseline migration creates the full schema, `unaccent`, `articles.search_vector`, and the GIN index on first boot.
