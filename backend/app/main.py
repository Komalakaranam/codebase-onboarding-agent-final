"""
FastAPI application entry point.

Run locally:
    cd backend
    uvicorn app.main:app --reload --port 8000

Then open http://127.0.0.1:8000/docs for interactive API documentation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import HealthResponse
from app.routers.evaluation import router as evaluation_router
from app.routers.onboarding import router as onboarding_router
from app.routers.qa import router as qa_router
from app.routers.repos import router as repos_router

app = FastAPI(
    title="Codebase Onboarding Agent",
    description=(
        "Ask natural-language questions about a GitHub codebase. "
        "This API clones repos, chunks code, embeds it, and answers via RAG."
    ),
    version="0.1.0",
)

# Local Vite dev server is always allowed; a deployed frontend (e.g. a
# Vercel URL) is added via ALLOWED_ORIGINS (comma-separated) so it never
# needs to be hardcoded here.
_extra_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *_extra_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos_router)
app.include_router(qa_router)
app.include_router(onboarding_router)
app.include_router(evaluation_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/debug/cors", tags=["system"])
def debug_cors():
    return {
        "allowed_origins_env_raw": settings.allowed_origins,
        "extra_origins_parsed": _extra_origins,
        "configured_allow_origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            *_extra_origins,
        ],
    }