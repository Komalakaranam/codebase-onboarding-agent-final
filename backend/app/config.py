"""
Application settings loaded from environment variables.

We use pydantic-settings so values can come from a .env file or the shell.
This keeps secrets (like GROQ_API_KEY) out of source code.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/ directory (one level above app/)
BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Groq LLM key — required later for the Q&A step, optional for step 1
    groq_api_key: str = ""

    # Where cloned GitHub repos are stored on disk
    data_dir: Path = BACKEND_ROOT / "data"

    # SQLite database file (used in step 6)
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'onboarding_agent.db'}"

    # ChromaDB persistent storage (step 3 — vector database for embeddings)
    chroma_dir: Path = BACKEND_ROOT / "chroma_db"

    # Local embedding model — free, runs on CPU, 384-dimensional vectors
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 64

    # Groq LLM used for step 4 (Q&A generation over retrieved chunks)
    groq_model_name: str = "openai/gpt-oss-20b"
    qa_top_k: int = 5

    # Extra CORS origins allowed to call this API, comma-separated (e.g. a
    # deployed Vercel frontend URL). Localhost is always allowed separately
    # in main.py so local dev keeps working regardless of this setting.
    allowed_origins: str = ""

    # File extensions we index in step 1
    supported_extensions: tuple[str, ...] = (".py", ".js", ".jsx", ".ts", ".tsx")

    # Directories to skip when walking a cloned repo
    skip_dirs: tuple[str, ...] = (
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "coverage",
    )


settings = Settings()

# Ensure runtime folders exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
