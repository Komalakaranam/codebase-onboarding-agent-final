"""
Question-answering service — step 4 of the RAG pipeline.

RAG = Retrieval-Augmented Generation. It's two separate jobs done by two
separate tools, glued together by this module:

  1. RETRIEVAL (ChromaDB's job): find which pieces of code are relevant
     to the question. ChromaDB has no idea what the code *means* or how
     to write English — it only knows how to compare vectors and return
     the closest ones. Fast, deterministic, no "creativity".

  2. GENERATION (Groq LLM's job): read the retrieved code and the question,
     then write a human-readable answer. The LLM has never seen this
     repository before and cannot browse it — it only knows what we paste
     into the prompt. Without step 1, we'd have to paste the *entire*
     codebase into every prompt (too big, too slow, too expensive).
     Without step 2, we'd just hand the user raw code snippets with no
     explanation.

Together: ChromaDB narrows millions of possible lines of code down to a
handful of relevant ones; Groq turns those few lines into a real answer.
"""

from __future__ import annotations

from groq import Groq

from app.config import settings
from app.models.schemas import AskQuestionResponse, SourceReference
from app.services.embeddings import embed_texts
from app.services.vector_store import get_stored_chunk_count, query_similar_chunks


class RepoNotIndexedError(Exception):
    """Raised when asking about a repo that has no vectors in ChromaDB yet."""


SYSTEM_PROMPT = (
    "You're a senior developer explaining this codebase to a teammate. "
    "Answer only from the code snippets below — never invent behavior that "
    "isn't shown.\n\n"
    "Write the way you'd talk: direct, plain sentences, no filler or hedging "
    "like 'based on the snippets provided.' If the answer has multiple parts "
    "or steps, use short bullet points instead of one long sentence.\n\n"
    "Cite the file and lines you're using, like (path/to/file.py:12-20).\n\n"
    "If the snippets don't fully cover the question, just say what's missing "
    "in a sentence — no formal disclaimer needed."
)


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a labeled block the LLM can cite from."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        label = f"[{i}] {meta['file_path']} (lines {meta['start_line']}-{meta['end_line']})"
        if meta.get("name"):
            label += f" — {meta['chunk_type']} `{meta['name']}`"
        language = meta.get("language", "")
        blocks.append(f"{label}\n```{language}\n{chunk['document']}\n```")
    return "\n\n".join(blocks)


def _get_groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    return Groq(api_key=settings.groq_api_key)


def answer_question(
    repo_id: str,
    question: str,
    top_k: int | None = None,
) -> AskQuestionResponse:
    """
    Full step-4 flow: embed question → retrieve chunks → ask Groq → cite sources.
    """
    if get_stored_chunk_count(repo_id) == 0:
        raise RepoNotIndexedError(
            f"Repo '{repo_id}' has no indexed chunks. Run POST /repos/index first."
        )

    top_k = top_k or settings.qa_top_k

    # --- Retrieval: turn the question into a vector, search ChromaDB ---
    # The question is embedded with the *same* model used for the code
    # chunks, so both live in the same 384-dimensional space and can be
    # compared directly.
    query_vector = embed_texts([question])[0]
    chunks = query_similar_chunks(repo_id, query_vector, top_k=top_k)

    if not chunks:
        return AskQuestionResponse(
            repo_id=repo_id,
            question=question,
            answer="No relevant code was found for this question in the indexed repository.",
            sources=[],
            model=settings.groq_model_name,
            chunks_retrieved=0,
        )

    # --- Generation: hand the retrieved code + question to the Groq LLM ---
    context = _build_context(chunks)
    user_prompt = (
        f"Context (retrieved code snippets, most relevant first):\n\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer clearly and cite the snippet file paths/line numbers you used."
    )

    client = _get_groq_client()
    completion = client.chat.completions.create(
        model=settings.groq_model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    answer = (completion.choices[0].message.content or "").strip()

    sources = [
        SourceReference(
            file_path=chunk["metadata"]["file_path"],
            chunk_type=chunk["metadata"]["chunk_type"],
            name=chunk["metadata"]["name"] or None,
            start_line=chunk["metadata"]["start_line"],
            end_line=chunk["metadata"]["end_line"],
            relevance_score=chunk["relevance_score"],
        )
        for chunk in chunks
    ]

    return AskQuestionResponse(
        repo_id=repo_id,
        question=question,
        answer=answer,
        sources=sources,
        model=settings.groq_model_name,
        chunks_retrieved=len(chunks),
    )
