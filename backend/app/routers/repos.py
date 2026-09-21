"""
Repository indexing endpoints.

POST /repos/index — clone a GitHub repo, parse source files, embed chunks,
                    and store vectors in ChromaDB (steps 1 + 3 of RAG).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import (
    IndexRepoRequest,
    IndexRepoResponse,
    IndexStatus,
    ParsedChunkPreview,
    RepoOverviewResponse,
)
from app.services.embeddings import embed_chunks, get_embedding_model
from app.services.github import GitHubCloneError, clone_github_repo
from app.services.overview import get_repo_overview
from app.services.parser import RepoTooLargeError, parse_repository
from app.services.qa import RepoNotIndexedError
from app.services.vector_store import get_stored_chunk_count, store_chunks

router = APIRouter(prefix="/repos", tags=["repos"])

logger = logging.getLogger(__name__)


def _preview_content(content: str, limit: int = 200) -> str:
    text = content.strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


@router.post("/index", response_model=IndexRepoResponse)
def index_repository(request: IndexRepoRequest) -> IndexRepoResponse:
    """
    Full indexing pipeline for a public GitHub repository.

    Flow:
      1. Clone repo → backend/data/
      2. Parse Python/JS files into code chunks
      3. Generate embeddings (sentence-transformers)
      4. Store vectors + metadata in ChromaDB
    """
    repo_url = str(request.repo_url)
    t_start = time.monotonic()

    # --- Step 1: Clone ---
    try:
        local_path, owner, repo_name = clone_github_repo(repo_url)
    except GitHubCloneError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    t_cloned = time.monotonic()

    repo_id = f"{owner}__{repo_name}"

    # --- Step 2: Parse ---
    try:
        chunks, files_scanned = parse_repository(local_path)
    except RepoTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Repository cloned but parsing failed: {exc}",
        ) from exc
    t_parsed = time.monotonic()

    # --- Step 3: Embed ---
    try:
        embeddings = embed_chunks(chunks)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Parsing succeeded but embedding failed: {exc}",
        ) from exc
    t_embedded = time.monotonic()

    # --- Step 4: Store in ChromaDB ---
    try:
        chunks_embedded = store_chunks(repo_id, chunks, embeddings)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Embedding succeeded but storage failed: {exc}",
        ) from exc
    t_stored = time.monotonic()

    logger.info(
        "Indexed %s: clone=%.2fs parse=%.2fs embed=%.2fs store=%.2fs total=%.2fs "
        "(files=%d chunks=%d, embedding model cache hits=%d misses=%d)",
        repo_id,
        t_cloned - t_start,
        t_parsed - t_cloned,
        t_embedded - t_parsed,
        t_stored - t_embedded,
        t_stored - t_start,
        files_scanned,
        len(chunks),
        get_embedding_model.cache_info().hits,
        get_embedding_model.cache_info().misses,
    )

    indexed_at = datetime.now(timezone.utc)

    preview_chunks = [
        ParsedChunkPreview(
            file_path=chunk.file_path,
            chunk_type=chunk.chunk_type,
            name=chunk.name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            content_preview=_preview_content(chunk.content),
        )
        for chunk in chunks[:50]
    ]

    return IndexRepoResponse(
        repo_id=repo_id,
        repo_url=repo_url,
        repo_name=f"{owner}/{repo_name}",
        local_path=str(local_path),
        status=IndexStatus.completed,
        files_scanned=files_scanned,
        chunks_found=len(chunks),
        chunks_embedded=chunks_embedded,
        embedding_model=settings.embedding_model_name,
        chunks=preview_chunks,
        indexed_at=indexed_at,
        message=(
            f"Indexed {files_scanned} files → {len(chunks)} chunks → "
            f"{chunks_embedded} embeddings stored in ChromaDB. "
            f"Ready for Q&A (step 4)."
        ),
    )


@router.get("/{repo_id}/summary")
def get_repo_summary(repo_id: str) -> dict:
    """Check how many vectors are stored for a repo in ChromaDB."""
    count = get_stored_chunk_count(repo_id)
    if count == 0:
        raise HTTPException(
            status_code=404,
            detail="Repo not found in vector store. Run POST /repos/index first.",
        )
    return {
        "repo_id": repo_id,
        "chunks_embedded": count,
        "embedding_model": settings.embedding_model_name,
        "vector_store": "chromadb",
    }


@router.get("/{repo_id}/overview", response_model=RepoOverviewResponse)
def get_repo_overview_endpoint(repo_id: str) -> RepoOverviewResponse:
    """
    Files scanned, chunks found, and detected languages come straight
    from disk/ChromaDB; the description is a short Groq-generated
    summary grounded in the repo's README (or a few retrieved chunks
    if there's no README).
    """
    try:
        return get_repo_overview(repo_id)
    except RepoNotIndexedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc