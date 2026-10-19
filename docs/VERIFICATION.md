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

- No Render service or paid disk was provisioned. The available connector cannot attach a persistent disk and no Render API credential is configured. Applying the prepared Blueprint in the Dashboard is the remaining hosting step; schema validation is not a deployment or platform admission test.
- No live Gemini generation was run. Provider success and failure paths were tested using isolated doubles; missing configuration was tested through the actual UI/backend.
- Docker containers and external TTS/OCR infrastructure were not executed. Existing APIs remain available and their local text/script paths were exercised.
- The audit resolves `backend/requirements_docker.txt`; it is not a security audit of all unrelated packages installed on the workstation or the optional ML stack.
- Automated accessibility tests supplement the visual/keyboard checks; they do not prove complete accessibility compliance.
- Shared workspace privacy and single-instance/in-process limits are documented in README and the implementation report.
