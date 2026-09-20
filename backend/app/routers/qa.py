"""
Question-answering + chat history endpoints — steps 4 and 6.

POST /repos/{repo_id}/ask
    1. Embed the question (sentence-transformers)
    2. Retrieve the top-k most similar code chunks (ChromaDB)
    3. Ask the Groq LLM to answer using those chunks (generation)
    4. Save the question/answer pair to SQLite (step 6)
    5. Return the answer plus the file/line references it was grounded in

GET /repos/{repo_id}/history
    Returns past Q&A pairs for a repo from SQLite, most recent first.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    AskQuestionRequest,
    AskQuestionResponse,
    ChatHistoryEntry,
    ChatHistoryResponse,
)
from app.services.history import get_chat_history, save_chat_entry
from app.services.qa import RepoNotIndexedError, answer_question

router = APIRouter(prefix="/repos", tags=["qa"])


@router.post("/{repo_id}/ask", response_model=AskQuestionResponse)
def ask_question(
    repo_id: str,
    request: AskQuestionRequest,
    db: Session = Depends(get_db),
) -> AskQuestionResponse:
    try:
        response = answer_question(repo_id, request.question, top_k=request.top_k)
    except RepoNotIndexedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        # e.g. GROQ_API_KEY missing from backend/.env
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc

    save_chat_entry(db, repo_id, response.question, response.answer)
    return response


@router.get("/{repo_id}/history", response_model=ChatHistoryResponse)
def get_repo_history(
    repo_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    entries = get_chat_history(db, repo_id, limit=limit)
    return ChatHistoryResponse(
        repo_id=repo_id,
        count=len(entries),
        history=[ChatHistoryEntry.model_validate(entry) for entry in entries],
    )
