"""
SQLite database — step 6: persists chat history across server restarts.

SQLAlchemy is already a dependency (see requirements.txt), and config.py
already reserved `database_url` for this step, so we use its ORM rather
than raw sqlite3 — it gives us a table definition, connection pooling, and
session handling in a few lines, with no hand-written SQL to maintain.

This module has no idea what ChromaDB or Groq are. It only stores and
retrieves rows — a completely separate concern from the RAG pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# check_same_thread=False: FastAPI can handle a single request's DB calls on
# a different thread than the one that opened the connection.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ChatHistory(Base):
    """One row per question asked via POST /repos/{repo_id}/ask."""

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(String, nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


# Create the table on import — mirrors config.py eagerly creating data
# directories, so there's no separate migration step to run by hand.
Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields one session per request, closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
