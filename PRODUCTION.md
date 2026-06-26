# Production Deployment Guide

This guide describes the production posture of the current Flask/React Docker app and the recommended migration path for a larger multi-user deployment.

## Current Runtime

- Frontend: React static build served by Nginx.
- Backend: Flask served by Waitress.
- Persistence: SQLite WAL under the mounted `scientia-data` Docker volume.
- Retrieval: lexical by default, optional FAISS/sentence-transformers when enabled.
- Jobs: bounded in-process thread pool for async PDF processing.
- Observability: request IDs, response-time headers, health/readiness/metrics endpoints.

## Environment Configuration

Create a `.env` file from `.env.example` and set production values:

```env
APP_NAME=Scientia.ai
APP_VERSION=1.0.0
ENVIRONMENT=production
SECRET_KEY=replace_with_a_strong_secret
CORS_ORIGINS=https://your-frontend.example.com
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_optional_github_token_here
DATABASE_URL=sqlite:////app/data/scientia.db
RATE_LIMIT_PER_MINUTE=120
RATE_LIMIT_WINDOW_SECONDS=60
JOB_WORKERS=3
JOB_MAX_IN_FLIGHT=50
JOB_RETENTION_LIMIT=500
MAX_UPLOAD_MB=50
```

## Deploy With Docker Compose

```bash
docker-compose up --build -d
```

Health checks:

```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/api/system/readiness
curl http://localhost:5000/api/system/metrics
```

## Operational Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Backward-compatible health plus dependency snapshot. |
| `GET /api/system/health` | Detailed dependency, SLO, and scale-limit snapshot. |
| `GET /api/system/readiness` | Returns `503` when database or storage is unavailable. |
| `GET /api/system/metrics` | Queue, rate limiter, and retrieval counters. |

Every response includes `X-Request-ID` and `X-Response-Time-ms`. Propagate `X-Request-ID` from the frontend or API gateway when debugging user reports.

## Security Hardening Checklist

- Set a strong `SECRET_KEY` and keep `.env` out of source control.
- Restrict `CORS_ORIGINS` to your deployed frontend domain.
- Terminate TLS at a reverse proxy, cloud load balancer, or CDN.
- Protect `/api/settings`, `/api/generated-outputs`, and metrics routes with authentication before public exposure.
- Store uploads and generated artifacts on encrypted storage.
- Rotate Gemini/GitHub tokens and prefer provider-side least-privilege controls.
- Add malware scanning if accepting untrusted PDFs from public users.

## Capacity And Backpressure

- `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_WINDOW_SECONDS` limit API bursts per caller key.
- `JOB_WORKERS` controls concurrent background work.
- `JOB_MAX_IN_FLIGHT` caps queued plus running jobs; saturated async upload returns `429 job_queue_full`.
- `JOB_RETENTION_LIMIT` bounds retained job metadata.
- `MAX_UPLOAD_MB`, `MAX_ANALYSIS_CHARS`, and `MAX_QA_CONTEXT_CHARS` bound expensive request sizes.

## Backup And Restore

Back up the Docker volume or mounted data folder containing:

- `scientia.db`, `scientia.db-wal`, and `scientia.db-shm`
- `uploads/`
- `faiss_index/`
- `generated_audio/`
- `generated_code/`
- `generated_markdown/`

For SQLite, take backups during low write activity or use the SQLite backup API in a maintenance script.

## Scale-Out Roadmap

The current app is intentionally dependency-light. For a larger production system, migrate in this order:

1. Move SQLite to PostgreSQL and add migrations.
2. Move the in-process job manager to Redis/Celery, Cloud Tasks, or another durable queue.
3. Move uploads and generated artifacts to object storage.
4. Move API rate limiting to Redis or the API gateway.
5. Split PDF processing and retrieval indexing into worker services.
6. Add user auth, tenant/workspace IDs, and authorization checks.
7. Add OpenTelemetry traces, Prometheus metrics, and alerting.

See `docs/SYSTEM_DESIGN.md` for architecture diagrams, data flow, tradeoffs, and failure modes.