# Implementation report

## Original application and audit

The supplied workspace was already an extracted Git repository, with a configured GitHub origin and existing local changes. No ZIP extraction was needed. The active implementation was React 18/Create React App plus Flask/Waitress, SQLite WAL, PyMuPDF, optional Gemini, lexical/FAISS retrieval, OCR, citations, GitHub matching, code scaffolding, podcast scripts/audio, background upload jobs, and health endpoints. An unused partial FastAPI application also existed.

Initial findings, prioritized:

| Priority | Finding | Change |
| --- | --- | --- |
| P0 | App imported multiple absent components and could not build | Implemented a complete working workspace and replaced missing imports |
| P0 | Frontend could bake an admin key into JavaScript and a browser cookie | Removed frontend key handling and Docker build arguments |
| P0 | Pages requests used relative APIs and lacked a deployment workflow | Explicit public backend origin, capability states, base-aware build and Pages workflow |
| P0 | Shared mutable retrieval index could switch between concurrent requests/uploads | Serialized index selection and retrieval across requests/jobs with a reentrant lock |
| P1 | Research agent rejected orchestration arguments | Accepted shared agent context and exercised the real dispatch path |
| P1 | Legacy build had a large deprecated dependency tree | Kept React, moved build/test tooling to Vite/Vitest, removed unused runtime/CSS dependencies, updated vulnerable packages |
| P1 | Gemini transport had no explicit timeout and exposed raw provider exceptions | Server-side REST header authentication, bounded response/timeout, sanitized errors |
| P1 | No dependable general scholarly discovery workflow | Public Crossref discovery with metadata normalization, filtering, sorting and pagination |
| P1 | Invalid JSON types could cause route errors | Added JSON-object and common-field validation plus bounded research-specific schemas |
| P1 | Rate limiting trusted client-supplied forwarding headers; aliases bypassed it | Use connection address and include legacy expensive aliases |
| P1 | Query-string admin credentials could leak through URLs | Removed query parameter admin authentication; retained protected headers/server cookies |
| P1 | Local tools could be mislabeled as cloud-generated results | Explicit local/provider/metadata modes; fallback state is thread-local |
| P1 | Reloading a PDF lost analysis mode and structured agent fields | Added a backward-compatible SQLite metadata column and persisted analysis fields |
| P1 | Equation API accepted arbitrary server image paths | Require uploaded images rather than client-specified filesystem paths |
| P2 | Citation enrichment could issue 20 serial network calls | Bound external lookups to three, cache results, keep raw reference extraction |
| P2 | Disabled ML features still imported the heavyweight transformer stack | Lazy-load transformers and sentence-transformers only when enabled |
| P2 | Missing favicon and external formula scripts were unnecessary | Added a local SVG favicon; removed unused remote scripts |
| P2 | Production requirements installed the unused FastAPI stack | Point production requirements at the actual lightweight Flask runtime |

The baseline passed 15 backend tests, but those tests did not establish frontend viability or complete document workflows. Existing deleted components and FastAPI endpoints were already absent before edits and were not restored over local work.

## Implemented experience

- Evidence-focused landing page with editorial typography, green neutral palette, responsive cards, mobile navigation, collapsible desktop sidebar, and persistent light/dark themes.
- Crossref discovery by topic/title/author with date filters, relevance/citation/date ordering, pagination, abstracts and available PDF links, request cancellation, timeout, bounded transient retry, explicit failure and empty states.
- Local bookmarks, notes, search history, citation copies, BibTeX/text exports and workspace JSON export.
- DOI-based review selection and a metadata comparison table with Markdown export; Gemini-backed reviews retrieve metadata on the server instead of trusting client-supplied evidence.
- Research chat retrieves scholarly evidence, carries bounded follow-up context, displays linked source metadata, and labels AI analysis and uncertainty.
- Uploaded-paper workspace preserves the original extraction/analysis tools. It supports asynchronous progress, reloading documents, cross-document QA, Gemini PDF comparison, reports, source page links, citation extraction, briefing scripts and the specialized chat tools.
- Markdown/GFM reports render lazily, with raw HTML disabled, safe links, readable tables and code blocks.

No production fixtures or simulated AI responses were introduced. Test publisher data and provider doubles are isolated under test code.

## Verification and remaining access

See `docs/VERIFICATION.md` for final test results. Desktop and mobile screenshots were captured from the production build and visually inspected.

The Render Blueprint was validated against `https://render.com/schema/render.yaml.json`. A real Crossref search returned HTTP 200. Live Gemini generation requires a server-side credential and has not been exercised. Docker was prepared but not executed.

The initial restricted GitHub check reported an invalid token, but a network-enabled check verified valid authentication and repository write access. Source was committed and pushed, preserving the remote notebook update. GitHub Pages was enabled and deployed successfully: [live site](https://pruthvi226.github.io/AI_Research_Assistant/), [deployment run](https://github.com/Pruthvi226/AI_Research_Assistant/actions/runs/39264404488). A browser verified real search, bookmarks, saved notes after reload, mobile navigation, themes and clean asset loading.

No paid Render resource was created. The connected Render tool cannot attach the required persistent disk, and no Render API key or Gemini credential is configured. The prepared Blueprint is published and its Dashboard application link is in README. Backend deployment awaits that user-controlled step.

## Architectural limits

The backend remains a shared demonstration workspace. It does not implement user accounts, tenant ownership, or end-to-end private document authorization. Admin authentication covers administrative operations, not full user isolation. This is explicitly stated in the interface and README. Confidential/multi-user production launch requires those controls.

SQLite, one in-memory retrieval index, a serialization lock, in-process jobs, and in-memory rate limits favor a small single-instance deployment. The lock fixes result correctness while reducing concurrency. A future design should move retrieval to isolated per-document indexes, use durable workers and shared limits, and store large files in object storage.

Academic metadata is not a substitute for full-text verification. Crossref may omit fields; DOI enrichment and OpenAlex title matching should be checked manually for high-stakes work. Reviews and gap hypotheses are bounded by the supplied abstracts. The retained audio API depends on external services; no audio playback was newly claimed.

## Documentation references used

- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [GitHub official Pages workflow guidance](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec) and [disk constraints](https://render.com/docs/disks)
- [Gemini API reference](https://ai.google.dev/api)
- [Vite](https://vite.dev/guide/) and [Vitest](https://vitest.dev/guide/)

Backend infrastructure preparation used the installed Render Blueprints skill; no external communication or infrastructure creation was performed.
