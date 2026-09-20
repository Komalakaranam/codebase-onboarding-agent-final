"""
Chat history service — step 6.

Plain CRUD over the `chat_history` SQLite table. Every question asked via
POST /repos/{repo_id}/ask gets saved here so a user can revisit past Q&A
without re-running retrieval or paying for another Groq call. This module
never touches ChromaDB or Groq — it only reads/writes rows.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import ChatHistory


def save_chat_entry(db: Session, repo_id: str, question: str, answer: str) -> ChatHistory:
    """Insert one Q&A pair after a successful /ask call."""
    entry = ChatHistory(repo_id=repo_id, question=question, answer=answer)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_chat_history(db: Session, repo_id: str, limit: int = 50) -> list[ChatHistory]:
    """Most recent Q&A pairs for a repo, newest first."""
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.repo_id == repo_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
