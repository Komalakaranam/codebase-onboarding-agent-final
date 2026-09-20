# Codebase Onboarding Agent

AI-powered tool that lets developers ask natural language questions about a GitHub codebase and get answers with source references (RAG-based).

## Tech stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI (Python) |
| Frontend | React + Vite *(step 7)* |
| Database | SQLite |
| Vector store | ChromaDB |
| LLM | Groq (`openai/gpt-oss-20b`) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |

## Project layout

```
codebase-onboarding-agent/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point + CORS config
│   │   ├── config.py        # Settings & paths
│   │   ├── database.py      # SQLAlchemy engine + ChatHistory model (SQLite)
│   │   ├── models/          # Request/response schemas
│   │   ├── routers/         # API routes (repos.py, qa.py)
│   │   └── services/        # Clone, parse, embed, retrieve, qa, history
│   ├── data/                # Cloned repos (gitignored)
│   ├── requirements.txt
│   └── .env.example
└── frontend/                 # React (Vite) UI — Index / Chat / History views
    ├── src/
    │   ├── api.js            # All fetch() calls to the backend live here
    │   ├── App.jsx            # Tab navigation between the 3 views
    │   └── components/
    └── .env.example
```

## Backend setup (step 1)

**Prerequisites:** Python 3.11+, [Git](https://git-scm.com/) installed.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Start the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000/docs** and try `POST /repos/index` with:

```json
{
  "repo_url": "https://github.com/tiangolo/fastapi"
}
```

Then ask a question with `POST /repos/{repo_id}/ask` (the `repo_id` is in
the index response, e.g. `tiangolo__fastapi`), and view past Q&A with
`GET /repos/{repo_id}/history`.

## Frontend setup (step 7)

**Prerequisites:** Node 18+, the backend already running on port 8000.

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. See `frontend/README.md` for how the
frontend talks to the backend (and why CORS matters here).

## Current progress

- [x] **Step 1** — Clone GitHub repo + parse Python/JS files
- [x] **Step 3** — Embeddings (sentence-transformers) + ChromaDB storage
- [x] **Step 4** — Question answering via Groq (retrieval + generation)
- [x] **Step 6** — SQLite chat history
- [x] **Step 7** — React frontend (Index / Chat / History views)
- [ ] Step 2 — Intelligent chunking refinements (basic chunking done in step 1)
- [ ] Step 5 — Source references in answers *(shipped as part of step 4)*
