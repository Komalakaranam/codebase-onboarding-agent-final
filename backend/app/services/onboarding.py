"""
Onboarding guide service — backs the Onboarding tab.

Gathers the material a new teammate would actually read first (README,
common config/manifest files, and a handful of retrieved "key" code
chunks — entry points, core modules) and asks Groq to turn that into a
structured Markdown guide. Reuses overview.py's README/path helpers
rather than duplicating them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models.schemas import OnboardingGuideResponse
from app.services.embeddings import embed_texts
from app.services.llm_client import get_groq_client
from app.services.overview import _find_readme, _local_repo_path
from app.services.qa import RepoNotIndexedError
from app.services.vector_store import get_stored_chunk_count, query_similar_chunks

CONFIG_FILENAMES = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "go.mod",
    "Cargo.toml",
    "setup.py",
]
CONFIG_FILE_MAX_CHARS = 2000

KEY_CHUNK_QUERY = "main entry point, application startup, server initialization, core module"
KEY_CHUNK_TOP_K = 6

SYSTEM_PROMPT = (
    "You're a senior developer writing an onboarding guide for a new "
    "teammate joining this project. Using only the material given below "
    "(README, config files, and key code snippets), write a structured "
    "Markdown guide with exactly these five sections, in this order:\n\n"
    "## Project Overview\n## Technology Stack\n## Project Structure\n"
    "## Key Components\n## Setup Instructions\n\n"
    "Keep it concise and practical — short paragraphs or bullet points, no "
    "filler. Cite file paths where relevant. If setup steps aren't clear "
    "from the material, say so briefly under Setup Instructions instead of "
    "guessing at commands that aren't shown."
)


def _read_config_files(local_path: Path) -> str:
    blocks = []
    for filename in CONFIG_FILENAMES:
        path = local_path / filename
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")[:CONFIG_FILE_MAX_CHARS]
            except OSError:
                continue
            blocks.append(f"# {filename}\n{content}")
    return "\n\n".join(blocks)


def _key_code_chunks(repo_id: str) -> str:
    query_vector = embed_texts([KEY_CHUNK_QUERY])[0]
    chunks = query_similar_chunks(repo_id, query_vector, top_k=KEY_CHUNK_TOP_K)

    blocks = []
    for chunk in chunks:
        meta = chunk["metadata"]
        label = f"{meta['file_path']} (lines {meta['start_line']}-{meta['end_line']})"
        if meta.get("name"):
            label += f" — {meta['chunk_type']} `{meta['name']}`"
        language = meta.get("language", "")
        blocks.append(f"# {label}\n```{language}\n{chunk['document']}\n```")
    return "\n\n".join(blocks)


def generate_onboarding_guide(repo_id: str) -> OnboardingGuideResponse:
    if get_stored_chunk_count(repo_id) == 0:
        raise RepoNotIndexedError(
            f"Repo '{repo_id}' has no indexed chunks. Run POST /repos/index first."
        )

    local_path = _local_repo_path(repo_id)
    if not local_path.is_dir():
        raise RepoNotIndexedError(
            f"Repo '{repo_id}' is indexed but its local clone is missing "
            "(was backend/data/ cleared?). Re-index to restore it."
        )

    material_sections = []

    readme = _find_readme(local_path)
    if readme:
        material_sections.append(f"# README\n{readme}")

    config_files = _read_config_files(local_path)
    if config_files:
        material_sections.append(f"# Config / manifest files\n{config_files}")

    key_chunks = _key_code_chunks(repo_id)
    if key_chunks:
        material_sections.append(f"# Key code snippets\n{key_chunks}")

    material = "\n\n".join(material_sections) or "No README, config files, or indexed code were available."

    client = get_groq_client()
    completion = client.chat.completions.create(
        model=settings.groq_model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Project material:\n\n{material}\n\nWrite the onboarding guide.",
            },
        ],
        temperature=0.3,
        max_tokens=1600,
    )
    guide_markdown = (completion.choices[0].message.content or "").strip()

    return OnboardingGuideResponse(
        repo_id=repo_id,
        guide_markdown=guide_markdown,
        generated_at=datetime.now(timezone.utc),
    )
