# Contributing

## Local Setup

Backend:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Frontend:

```bash
cd frontend
npm install
npm start
```

## Verification

Run the backend quality gate:

```bash
python scripts/verify_backend.py
```

Run the optional Flask smoke check:

```bash
python scripts/verify_backend.py --smoke
```

Build the frontend without touching the checked-in `frontend/build` folder:

```powershell
cd frontend
$env:BUILD_PATH="../.codex-test/frontend-build"
npm run build
```

## Code Standards

- Keep changes scoped to the feature or bug being solved.
- Prefer existing project patterns over introducing new frameworks.
- Add or update tests for retrieval, jobs, API utilities, and routing behavior when changing those paths.
- Keep generated data, logs, local builds, caches, and secrets out of commits.
- Update `docs/API_CONTRACT.md` when changing request or response shapes.
- Update `docs/SYSTEM_DESIGN.md` when changing architecture boundaries or scale assumptions.

## Pull Request Checklist

- Backend verifier passes.
- Frontend production build passes.
- New endpoints are documented.
- Environment variables are added to `.env.example` when needed.
- No secrets, local databases, generated builds, or cache folders are included.