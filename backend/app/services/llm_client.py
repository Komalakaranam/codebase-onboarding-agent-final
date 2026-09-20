"""
Shared Groq client helper for LLM calls outside the step-4 Q&A flow
(overview description, onboarding guide generation, etc). qa.py keeps
its own copy since it shipped first and works fine — this just avoids
a third copy of the same four lines.
"""

from __future__ import annotations

from groq import Groq

from app.config import settings


def get_groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    return Groq(api_key=settings.groq_api_key)
