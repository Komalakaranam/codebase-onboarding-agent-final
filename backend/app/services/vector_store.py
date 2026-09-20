"""
ChromaDB vector store — saves embeddings and metadata for fast similarity search.

WHAT IS A VECTOR DATABASE?
--------------------------
A regular database finds rows where a column *equals* a value.
A vector database finds rows whose embedding is *closest* to your query
vector — measured by cosine distance or similar metrics.

ChromaDB stores, per chunk:
  - id          : unique key
  - embedding   : the 384-number vector from sentence-transformers
  - document    : the raw source code (returned to the LLM in step 4)
  - metadata    : file_path, function name, line numbers, etc.

We create one ChromaDB *collection* per repository so searches never
mix chunks from different codebases.
"""

from __future__ import annotations

import re
from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import settings
from app.services.parser import CodeChunk


def _sanitize_collection_name(repo_id: str) -> str:
    """
    Chroma collection names must be 3–63 chars, alphanumeric + underscores.

    repo_id looks like "encode__uvicorn" → collection "repo_encode_uvicorn"
    """
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", repo_id)
    name = f"repo_{safe}"
    if len(name) < 3:
        name = f"repo_{safe}_col"
    return name[:63]


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.ClientAPI:
    """Single persistent Chroma client — data survives server restarts."""
    return chromadb.PersistentClient(path=str(settings.chroma_dir))


def get_repo_collection(repo_id: str) -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=_sanitize_collection_name(repo_id),
        metadata={"hnsw:space": "cosine"},  # cosine similarity for semantic search
    )


def _chunk_id(repo_id: str, chunk: CodeChunk, index: int) -> str:
    """Stable unique ID — file + start line + index avoids collisions."""
    name_part = (chunk.name or "anon").replace(" ", "_")
    return f"{repo_id}::{chunk.file_path}::{chunk.start_line}::{name_part}::{index}"


def _chunk_metadata(repo_id: str, chunk: CodeChunk) -> dict[str, str | int]:
    """
    Metadata attached to each vector.

    Chroma only accepts str, int, float, bool — no None values.
    """
    return {
        "repo_id": repo_id,
        "file_path": chunk.file_path,
        "chunk_type": chunk.chunk_type,
        "name": chunk.name or "",
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "language": chunk.language,
    }


def delete_repo_collection(repo_id: str) -> None:
    """Remove a repo's collection before re-indexing."""
    client = get_chroma_client()
    name = _sanitize_collection_name(repo_id)
    try:
        client.delete_collection(name)
    except ValueError:
        pass  # collection didn't exist yet


def store_chunks(
    repo_id: str,
    chunks: list[CodeChunk],
    embeddings: list[list[float]],
) -> int:
    """
    Persist all chunk embeddings into ChromaDB.

    Returns the number of vectors stored.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunk/embedding count mismatch: {len(chunks)} vs {len(embeddings)}"
        )
    if not chunks:
        return 0

    # Fresh index — drop old vectors if user re-indexes the same repo
    delete_repo_collection(repo_id)
    collection = get_repo_collection(repo_id)

    ids = [_chunk_id(repo_id, chunk, i) for i, chunk in enumerate(chunks)]
    documents = [chunk.content for chunk in chunks]
    metadatas = [_chunk_metadata(repo_id, chunk) for chunk in chunks]

    # Chroma recommends batches ≤ ~5000 for large inserts
    batch_size = 500
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    return len(chunks)


def query_similar_chunks(
    repo_id: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """
    Semantic search: find the top_k stored chunks whose embeddings are
    closest to query_embedding (i.e. closest in meaning to the question).

    This is the "R" in RAG — Chroma does a nearest-neighbor search over
    every vector in the collection and returns the closest matches,
    ordered from most to least similar.

    Returns a list of dicts (most similar first):
        {"document": <source code>, "metadata": {...}, "relevance_score": 0-1}
    """
    collection = get_repo_collection(repo_id)
    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    chunks = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        # Cosine distance ranges 0 (identical) to 2 (opposite). Flip it into
        # an intuitive 0-1 "relevance" score for the API response.
        relevance_score = max(0.0, 1.0 - (distance / 2.0))
        chunks.append(
            {
                "document": document,
                "metadata": metadata,
                "relevance_score": round(relevance_score, 4),
            }
        )
    return chunks


def get_stored_chunk_count(repo_id: str) -> int:
    """How many vectors exist for this repo (0 if not indexed)."""
    try:
        collection = get_repo_collection(repo_id)
        return collection.count()
    except Exception:
        return 0
