# Verification results

Validated on 19 October 2026. Local verification results are below; the frontend was subsequently published and checked publicly as recorded in the deployment section.

| Check | Result |
| --- | --- |
| Python source parsing | 77 files passed |
| Backend tests | 29 passed |
| Health/readiness/metrics smoke endpoints | Four endpoints returned HTTP 200 with request IDs |
| Frontend ESLint | Passed, zero warnings |
| Frontend Vitest | 6 passed |
| Static production browser suite | 6 passed |
| Connected frontend + real Flask PDF workflow | 1 passed |
| Live Crossref browser test | 1 passed; real API HTTP 200 and DOI-linked publication cards |
| Accessibility | axe WCAG 2 A/AA and 2.1 AA checks passed for landing at 1440, 768, 390 px and dark search results |
| Responsive overflow | No horizontal overflow at the three tested widths |
| Production base path | `/AI_Research_Assistant/` build and direct hash navigation passed |
| Frontend dependency audit | Zero known vulnerabilities at audit time, including development dependencies |
| Backend runtime requirements audit | 30 resolved packages, zero known vulnerabilities at audit time |
| Render Blueprint | Valid against the current remote JSON Schema |
| Git whitespace validation | Passed |

The static browser suite deliberately skips the connected test unless `E2E_CONNECTED=true`; the live check is opt-in with `E2E_LIVE=true`. The connected and live checks were each executed separately and passed. Fixtures/provider doubles are confined to tests, except for the separate local generated PDF used for real processing checks.

Backend workflow coverage includes real PDF upload/extraction, asynchronous jobs and polling, persisted analysis mode on document reload, original PDF retrieval, source-grounded QA, history, Markdown export, research-agent dispatch, code scaffold compilation, equations, briefing scripts, negative payloads, bounded job queues, server-side provider headers and timeout, sanitized provider failures, missing AI credentials, review validation, metadata normalization, and concurrent document retrieval isolation.

Browser coverage includes search and filters, bookmarks, note persistence after reload, review selection, report download, upstream errors, empty results, hash routing/back navigation, theme persistence, keyboard skip navigation, offline capability controls, and real backend upload/chat/code/error workflows. No `pageerror` occurred in the core, connected, or live browser flow checks. This does not establish the absence of every possible console/network warning under every provider or deployment state.

## Build artifacts

The final discovery build used Vite's production mode with the GitHub repository base path. Outputs were approximately:

- Main JavaScript: 236.50 kB / 78.51 kB gzip.
- Lazy Markdown/GFM chunk: 155.25 kB / 46.39 kB gzip, loaded when an analysis/report is rendered.
- CSS: 23.81 kB / 5.43 kB gzip.
- HTML: 1.13 kB.

Local artifacts are under `.codex-test/production-build` and `.codex-test/connected-build` and are ignored by Git. Screenshots under `docs/screenshots/` are intentional documentation artifacts.

## Public deployment

- Live frontend: https://pruthvi226.github.io/AI_Research_Assistant/
- Successful Pages workflow: https://github.com/Pruthvi226/AI_Research_Assistant/actions/runs/39264404488
- Application release source commit: `3c9337059e76cef4943f7c603ededff382f7437c`.
- Public browser checks passed: HTTP 200, real Crossref search, DOI-linked publication cards, bookmarks, note persistence after reload, direct hash routes, mobile navigation, dark theme and static-mode capability state. Zero page errors and zero failed site assets were observed.
- GitHub authentication and repository write access were verified with network-enabled execution. The earlier restricted-environment authentication failure was not a real expired-token failure.

## Remaining unverified or pending

- The backend was subsequently deployed on Render's Free plan at the user's request. No paid disk was provisioned. Backend runtime data is ephemeral; see the free-hosting release record below.
- Live Gemini generation was initially unavailable; the subsequent authenticated verification is recorded below. Provider failure paths and missing configuration also have isolated regression coverage.
- Docker containers and external TTS/OCR infrastructure were not executed. Existing APIs remain available and their local text/script paths were exercised.
- The audit resolves `backend/requirements_docker.txt`; it is not a security audit of all unrelated packages installed on the workstation or the optional ML stack.
- Automated accessibility tests supplement the visual/keyboard checks; they do not prove complete accessibility compliance.
- Shared workspace privacy and single-instance/in-process limits are documented in README and the implementation report.

## Free-hosting release — 20 October 2026

- Frontend: https://pruthvi226.github.io/AI_Research_Assistant/
- Backend: https://scientia-research-api.onrender.com
- Render service: `srv-dbb69tgm7kps73c96rq0`, Singapore, **Free** compute plan, no persistent disk.
- Render deployment `dep-dbb69u0m7kps73c96t9g` reached **live**. Its source commit is `55eaa02b08f1eba062cadaf88321d5310c691efa`.
- The connected frontend release with document reopening and cold-start handling is `2329d3af89c17a376887cb34badf4a5a6b17a31d`.
- [Pages deployment](https://github.com/Pruthvi226/AI_Research_Assistant/actions/runs/39305533292) and [CI](https://github.com/Pruthvi226/AI_Research_Assistant/actions/runs/39305533315) both succeeded.
- `/api/health` and `/api/system/readiness` returned HTTP 200; readiness was true. CORS allowed the actual Pages origin. Health reported `storage_mode: ephemeral` and local fallback mode.
- The public browser workflow passed: temporary-storage notice, real PDF upload, local source-backed answer containing the document's dataset, original PDF page link returning PDF/HTTP 200, reopening the document and chat after reload, and actionable missing-Gemini-key handling. No page errors occurred.
- Testing exposed and fixed a document identifier mismatch in the frontend. The connected browser regression test now covers reopening after reload.
- Backend checks: 29 tests and four smoke endpoints passed. Frontend lint, six unit tests and production build passed. New startup code generates private runtime secrets if none were provisioned.
- Runtime storage is temporary. Backend PDFs/history can be lost on idle spin-down, restart or redeploy; browser notes/bookmarks are separate. A Gemini provider key remains required for generative AI. No paid disk or paid compute plan was created.

## Authenticated Gemini verification — 20 October 2026

After the user configured the Gemini key, a real request exposed a model-compatibility failure that the application had previously hidden behind a generic HTTP 502. The model configuration was migrated from legacy `gemini-2.5-flash` to `gemini-3.5-flash-lite`, preserving the user's key without reading or exposing it. Google documents restricted Gemini 2.5 access for new projects and recommends the current models: https://ai.google.dev/gemini-api/docs/deprecations/.

Source release: `469c2ef25e675795edd72a077e1ac3422b79cb54`. Render deploy `dep-dbbgcquh60os739uqa2g` reached **live**. [Pages deployment](https://github.com/Pruthvi226/AI_Research_Assistant/actions/runs/39379108625) and [CI](https://github.com/Pruthvi226/AI_Research_Assistant/actions/runs/39379108656) succeeded.

The actual public-site browser test passed all of the following with real Google generation, not provider doubles:

- Research answer with `mode: gemini` and six server-retrieved publication sources.
- Context-aware follow-up research answer.
- Real PDF upload and summary with `performance.mode: gemini`.
- Document QA with `artifacts.mode: gemini` and the correct dataset size from the PDF.
- A generated literature review using actual DOI-linked publications.
- Zero browser page errors during these workflows.

Regression checks passed: 31 backend tests, four smoke endpoints, frontend lint, six frontend tests and production build. Provider failures now distinguish quota limits, model access, rejected credentials and temporary outages without disclosing raw provider responses or credentials. The interface identifies configured AI accurately; request timeouts allow for cloud generation and free-host startup.
