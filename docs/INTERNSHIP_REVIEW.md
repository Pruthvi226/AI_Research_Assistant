# Internship Reviewer Guide

This project is positioned as a production-minded AI systems project, not only a UI demo. Use this guide to explain it in resumes, interviews, and portfolio reviews.

## One-Minute Pitch

Scientia.ai is a multi-agent research assistant that ingests papers, builds a retrieval index, routes user intent across specialized agents, and returns grounded summaries, answers, equations, citations, GitHub implementations, code scaffolds, and podcast briefings. The system includes persistence, background jobs, request tracing, health/readiness/metrics endpoints, Docker deployment, CI, and a scale-out architecture plan.

## What Makes It Internship-Level

- Full-stack product: React frontend, Flask backend, Docker deployment, and persistent storage.
- AI systems depth: RAG, source-grounded QA, agent routing, Gemini integration, and local fallback behavior.
- Systems thinking: bounded queues, backpressure, rate limiting, health/readiness/metrics, and deployment docs.
- Engineering hygiene: backend unit tests, syntax verifier, CI workflow, clear API contract, and production guide.
- User impact: turns dense research papers into actionable summaries, code, citations, and audio explanations.

## Demo Script

1. Upload a PDF and show async job progress or immediate summary.
2. Ask a source-grounded question and point to page-aware source chunks.
3. Trigger a specialized task such as code generation, citation analysis, GitHub matching, or podcast generation.
4. Open `/api/system/health` and `/api/system/metrics` to show operational thinking.
5. Show `docs/SYSTEM_DESIGN.md` and explain the migration path from single-node demo to distributed production.

## Design Tradeoffs To Discuss

| Decision | Tradeoff |
| --- | --- |
| Flask API | Simple and reliable for demo speed; can migrate to FastAPI or split services later. |
| SQLite WAL | Great local durability with minimal setup; PostgreSQL is the next step for multi-user scale. |
| In-process jobs | Low operational burden; production migration path is Redis/Celery or managed queues. |
| Lexical retrieval default | Works without model downloads; semantic FAISS can be enabled for higher recall. |
| Gemini optional | Better answer quality when configured; local fallback keeps the app demoable without keys. |

## Quality Gates

Run before demo or submission:

```bash
python scripts/verify_backend.py
```

Optional local smoke check with Flask imports:

```bash
python scripts/verify_backend.py --smoke
```

Frontend build on Windows/OneDrive-safe output:

```powershell
cd frontend
$env:BUILD_PATH="../.codex-test/frontend-build"
npm run build
```

## Resume Bullets

- Built a full-stack multi-agent AI research assistant with Flask, React, Gemini, SQLite, RAG retrieval, OCR, TTS, and Docker.
- Designed source-grounded QA over uploaded PDFs with page-aware chunks, lexical/FAISS retrieval modes, and local fallback behavior.
- Added production-style controls including request tracing, health/readiness/metrics endpoints, bounded async jobs, rate limiting, and CI verification.
- Documented system architecture, API contracts, SLO targets, failure modes, and scale-out migration from SQLite/in-process jobs to PostgreSQL, object storage, and durable queues.

## Next High-Leverage Improvements

- Add authentication, user workspaces, and authorization around generated outputs.
- Add retrieval evaluation datasets for answer faithfulness and citation accuracy.
- Move the queue and database to durable multi-instance infrastructure.
- Add OpenTelemetry traces and Prometheus-compatible metrics.