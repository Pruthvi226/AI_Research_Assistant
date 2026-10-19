# API Contract

Base URL in local development: `http://localhost:5000`.

## Research workspace additions

- `POST /api/research/answer`: JSON `{ "question": "...", "history": [{ "role": "user", "content": "..." }] }`. Question is 2–4000 characters; at most ten history messages. The backend retrieves publication evidence from Crossref. Returns `{ response, sources, mode: "gemini", evidence }`; sources include title, authors, year, URL and available abstract. Requires server-side Gemini configuration. Missing configuration: 503. Provider/metadata failure: 502. Invalid payload: 400.
- `POST /api/research/review`: JSON `{ "paper_ids": ["10.xxxx/a", "10.xxxx/b"] }`. Accepts two to eight distinct DOIs. The backend retrieves metadata concurrently with bounded requests and generates an abstract-level literature review. Same response/error contract as research answers. Missing fields must remain unreported; proposed gaps are hypotheses.
- `POST /api/synthesis`: alias for the retained uploaded-PDF comparison endpoint. Body `{ "session_ids": ["id1", "id2"] }`, two to eight documents. Requires Gemini. Returns `{ headers, comparisons }`.
- `GET /api/documents/{id}/file`: original PDF, with a validated path under the configured upload folder. Frontend source links use `#page=N`.

New research endpoints return at least `{ error: "actionable message" }` for failures; older endpoints may additionally include the fields below. No API key is returned by these routes. Document/AI output modes distinguish Gemini, local extraction/templates, and metadata tools. The backend is a shared demonstration workspace; there is no private per-user document ownership.

All JSON error responses follow this shape:

```json
{
  "error": "Human-readable message",
  "code": "machine_readable_code",
  "details": {},
  "status": 400
}
```

Most API responses include:

- `X-Request-ID`: caller-provided or generated request correlation ID.
- `X-Response-Time-ms`: backend processing time in milliseconds.

## Health And Operations

### `GET /api/health`

Backward-compatible health endpoint with dependency snapshot.

Response highlights:

```json
{
  "status": "ok",
  "service": "Scientia.ai",
  "mode": "offline (fast local fallback)",
  "retrieval": "lexical",
  "checks": {
    "database": { "status": "ok" },
    "storage": { "status": "ok" },
    "jobs": { "status": "ok" }
  }
}
```

### `GET /api/system/health`

Detailed system health, runtime warnings, SLO targets, and scale limits.

### `GET /api/system/readiness`

Readiness gate for deployment platforms. Returns `503` when required database or storage dependencies are unavailable.

### `GET /api/system/metrics`

Runtime counters for job queue, rate limiter, and retrieval state.

## Documents

### `POST /api/upload/pdf`

Uploads, parses, chunks, indexes, analyzes, and stores a PDF.

Request: `multipart/form-data`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `file` | PDF file | yes | Limited by `MAX_UPLOAD_MB`. |

Response highlights:

```json
{
  "session_id": "paper_123",
  "filename": "paper.pdf",
  "summary": { "abstract": "...", "sections": {} },
  "references": {},
  "performance": { "mode": "local_extractive", "chunks": 12 }
}
```

### `POST /api/upload/pdf?async=true`

Accepts long PDF processing as a background job.

Response `202`:

```json
{
  "job_id": "uuid",
  "status": "queued",
  "status_url": "/api/jobs/uuid"
}
```

When the in-process queue is saturated, returns `429` with code `job_queue_full`.

### `GET /api/documents`

Lists uploaded documents.

### `GET /api/documents/{id}`

Returns a saved document summary and metadata.

### `DELETE /api/documents/{id}`

Deletes a document, chunks, chat history, and generated outputs for the document.

### `GET /api/documents/{id}/export/markdown`

Exports a markdown research report and saves it as a generated output.

## Chat And Agents

### `POST /api/chat`

Routes a user query through the orchestrator and selected agent.

Request:

```json
{
  "query": "What is the main contribution?",
  "session_id": "paper_123",
  "agent": "rag"
}
```

Response highlights:

```json
{
  "selected_agent": "RAG Retrieval Agent",
  "intent": "source_grounded_qa",
  "response": "...",
  "sources": ["[Source 1 | paper.pdf | page 2 | chunk 1] ..."],
  "artifacts": {}
}
```

### `GET /api/history?session_id={id}`

Returns ordered chat history for a document session.

## Specialized Agent Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/equation` | Analyze equation text or uploaded equation image. |
| `POST` | `/api/code` | Generate PyTorch code scaffold and downloadable artifact. |
| `POST` | `/api/citations` | Analyze references, citation context, and related work. |
| `POST` | `/api/github` | Search or summarize GitHub repositories for a research topic. |
| `POST` | `/api/podcast` | Generate podcast script and optional audio file. |
| `POST` | `/api/upload/image` | OCR equation image and analyze it. |

## Generated Outputs And Jobs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/jobs` | List recent background jobs. |
| `GET` | `/api/jobs/{job_id}` | Poll one job. |
| `GET` | `/api/generated-outputs` | List generated code/audio/markdown/equation outputs. |
| `GET` | `/api/generated-outputs/{id}` | Get generated output metadata and content. |
| `GET` | `/api/generated-outputs/{id}/download` | Download saved artifact or content fallback. |
