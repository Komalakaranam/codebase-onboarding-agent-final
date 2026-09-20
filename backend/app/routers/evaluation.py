"""
Retrieval evaluation — POST /repos/{repo_id}/evaluate.

Runs each test question through the real /ask pipeline and checks
whether the expected source file shows up in the retrieved sources.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import EvalRequest, EvalResponse
from app.services.evaluation import run_evaluation
from app.services.qa import RepoNotIndexedError

router = APIRouter(prefix="/repos", tags=["evaluation"])


@router.post("/{repo_id}/evaluate", response_model=EvalResponse)
def evaluate_repo(repo_id: str, request: EvalRequest) -> EvalResponse:
    try:
        return run_evaluation(repo_id, request)
    except RepoNotIndexedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc
