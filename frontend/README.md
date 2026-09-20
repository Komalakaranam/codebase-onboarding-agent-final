# Codebase Onboarding Agent — Frontend

React (Vite) UI for the RAG backend in `../backend`. Three views:

1. **Index Repo** — paste a GitHub URL, calls `POST /repos/index`.
2. **Chat** — ask questions about the indexed repo, calls `POST /repos/{repo_id}/ask`.
3. **History** — past Q&A pairs for the repo, calls `GET /repos/{repo_id}/history`.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local   # only needed if the backend isn't on 127.0.0.1:8000
npm run dev
```

Open **http://localhost:5173**. The backend must already be running (see
`../backend/README` / root `README.md`) — this app is a pure client that
talks to it over HTTP; it has no server of its own.

## How it talks to the backend

`src/api.js` is the only file that calls `fetch()`. Every component
(`RepoInput`, `Chat`, `History`) imports functions from it and never
constructs a request itself. The base URL comes from the
`VITE_API_BASE_URL` env var (default `http://127.0.0.1:8000`).

Because the dev server runs on a different origin
(`http://localhost:5173`) than the API (`http://127.0.0.1:8000`), the
browser enforces CORS: it will only let this page read the response if
the backend explicitly allows that origin. That's configured in
`backend/app/main.py`'s `CORSMiddleware` — see the root README for
details. Without it, every fetch above would fail with a CORS error
even though the backend itself works fine (e.g. via `/docs` or curl).

## Build

```bash
npm run build   # outputs to dist/
npm run lint    # oxlint
```
