"""
Embedding service — converts text into numerical vectors.

WHAT IS AN EMBEDDING?
---------------------
An embedding is a list of numbers (a "vector") that represents the *meaning*
of a piece of text. Similar meanings → similar vectors.

Example (simplified to 3 numbers; real models use 384+):
  "authenticate user"  → [0.82, 0.15, 0.44]
  "login function"     → [0.79, 0.18, 0.41]   ← close to above (similar meaning)
  "sort array"         → [0.12, 0.91, 0.05]   ← far away (different topic)

We use sentence-transformers with `all-MiniLM-L6-v2`:
  - Free, runs locally (no API cost)
  - Outputs 384-dimensional vectors
  - Good balance of speed vs. quality for a college project

WHY EMBEDDINGS FOR CODE SEARCH?
-------------------------------
Keyword search fails when the user's words don't match the code:
  Question: "How does user login work?"
  Code might say: `def authenticate(credentials)` — no word "login"

Embeddings capture *semantic similarity*, so "login" and "authenticate"
end up near each other in vector space. ChromaDB then finds the closest
vectors when we search in step 4.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.services.parser import CodeChunk


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model once and reuse it.

    First call downloads ~90 MB from Hugging Face (cached afterward).
    Keeping a single instance avoids reloading weights on every request.
    """
    return SentenceTransformer(settings.embedding_model_name)


def prepare_embed_text(chunk: CodeChunk) -> str:
    """
    Build the text we actually embed (may differ from stored document).

    Prepending file path + symbol name gives the model extra context so
    a question like "what does the run function do?" matches better.
    """
    header_parts = [f"file: {chunk.file_path}", f"type: {chunk.chunk_type}"]
    if chunk.name:
        header_parts.append(f"name: {chunk.name}")
    header = " | ".join(header_parts)
    return f"# {header}\n{chunk.content}"


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a batch of strings into embedding vectors.

    Batching is much faster than encoding one string at a time because
    the model can parallelize matrix math on CPU/GPU.
    """
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(
        texts,
        batch_size=settings.embedding_batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors.tolist()


def embed_chunks(chunks: list[CodeChunk]) -> list[list[float]]:
    """Embed all code chunks, returning one vector per chunk."""
    texts = [prepare_embed_text(chunk) for chunk in chunks]
    return embed_texts(texts)
