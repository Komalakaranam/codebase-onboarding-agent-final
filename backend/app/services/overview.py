"""
Repo overview service — backs the Overview tab.

Files/chunks/languages are cheap facts we already have on disk or in
ChromaDB, so we compute those directly instead of asking the LLM (fast,
free, deterministic). Only the project description needs the LLM: it
reads the repo's README if there is one, or falls back to a handful of
chunks retrieved from ChromaDB, and asks Groq for 2-3 plain sentences.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import settings
from app.models.schemas import RepoOverviewResponse
from app.services.embeddings import embed_texts
from app.services.llm_client import get_groq_client
from app.services.qa import RepoNotIndexedError
from app.services.vector_store import get_stored_chunk_count, query_similar_chunks

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
}

DESCRIPTION_SYSTEM_PROMPT = (
    "You're a senior developer writing a one-paragraph project summary for "
    "a teammate's first look at this repo. In 2-3 plain sentences, say what "
    "the project does and how it's put together. No headings, no bullet "
    "points, no hedging phrases — just the summary."
)

README_MAX_CHARS = 4000

logger = logging.getLogger(__name__)


def _local_repo_path(repo_id: str) -> Path:
    return settings.data_dir / repo_id


def _language_breakdown(local_path: Path) -> dict[str, int]:
    """File count per detected language — one pass covers both the
    language list and files_scanned (their sum), since LANGUAGE_BY_EXTENSION
    covers exactly the same extensions as settings.supported_extensions."""
    counts: dict[str, int] = {}
    for path in local_path.rglob("*"):
        if not path.is_file():
            continue
        if any(skip in path.parts for skip in settings.skip_dirs):
            continue
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return counts


def _find_readme(local_path: Path) -> str | None:
    for entry in sorted(local_path.iterdir()):
        if entry.is_file() and entry.name.lower().startswith("readme"):
            try:
                return entry.read_text(encoding="utf-8", errors="ignore")[:README_MAX_CHARS]
            except OSError:
                return None
    return None


def _context_from_chunks(repo_id: str) -> str | None:
    """Fallback when there's no README: summarize from a few retrieved chunks."""
    query_vector = embed_texts(
        ["project overview, main purpose, entry point, and setup"]
    )[0]
    chunks = query_similar_chunks(repo_id, query_vector, top_k=5)
    if not chunks:
        return None

    blocks = []
    for chunk in chunks:
        meta = chunk["metadata"]
        blocks.append(f"# {meta['file_path']}\n{chunk['document']}")
    return "\n\n".join(blocks)


def _generate_description(repo_id: str, local_path: Path) -> str:
    readme = _find_readme(local_path)
    if readme:
        source_label = "the project's README"
        material = readme
    else:
        material = _context_from_chunks(repo_id)
        source_label = "a sample of the project's code"
        if material is None:
            return "No README or indexed code was available to summarize this project."

    client = get_groq_client()
    completion = client.chat.completions.create(
        model=settings.groq_model_name,
        messages=[
            {"role": "system", "content": DESCRIPTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Here is {source_label}:\n\n{material}\n\nSummarize this project.",
            },
        ],
        temperature=0.3,
        # Some Groq-hosted models (e.g. openai/gpt-oss-*) are reasoning
        # models whose internal chain-of-thought also counts against
        # max_tokens. A tight budget here can let reasoning consume the
        # whole thing, finishing with finish_reason="length" and an empty
        # message.content — no error, just nothing to show. 500 leaves
        # room for that reasoning plus the actual 2-3 sentence summary.
        max_tokens=500,
    )
    description = (completion.choices[0].message.content or "").strip()
    if not description:
        finish_reason = getattr(completion.choices[0], "finish_reason", "unknown")
        logger.warning(
            "Groq returned an empty description for repo_id=%s "
            "(model=%s, finish_reason=%s). Full completion: %r",
            repo_id,
            settings.groq_model_name,
            finish_reason,
            completion,
        )
        return (
            "The model didn't return a summary for this repo (it may have run "
            "out of budget reasoning about it). Try again, or check the "
            "backend logs for the raw completion."
        )
    return description


def get_repo_overview(repo_id: str) -> RepoOverviewResponse:
    chunks_found = get_stored_chunk_count(repo_id)
    if chunks_found == 0:
        raise RepoNotIndexedError(
            f"Repo '{repo_id}' has no indexed chunks. Run POST /repos/index first."
        )

    local_path = _local_repo_path(repo_id)
    if not local_path.is_dir():
        raise RepoNotIndexedError(
            f"Repo '{repo_id}' is indexed but its local clone is missing "
            "(was backend/data/ cleared?). Re-index to restore it."
        )

    language_breakdown = _language_breakdown(local_path)

    return RepoOverviewResponse(
        repo_id=repo_id,
        files_scanned=sum(language_breakdown.values()),
        chunks_found=chunks_found,
        languages=sorted(language_breakdown.keys()),
        language_breakdown=language_breakdown,
        description=_generate_description(repo_id, local_path),
    )
