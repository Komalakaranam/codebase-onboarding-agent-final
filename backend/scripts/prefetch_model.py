"""
Pre-downloads the sentence-transformers embedding model at build time.

Without this, the model (~90MB from Hugging Face) is only fetched lazily
on the first request that actually needs embeddings (get_embedding_model()
in app/services/embeddings.py is @lru_cache'd). On a host with ephemeral
disk — e.g. Render's free tier — that means the first real indexing
request after every fresh deploy pays for a live download on top of
normal cold-start latency, which risks a request timeout.

Run this as part of the platform's build command, after installing
dependencies, so the model is already cached before the app starts
serving traffic:

    pip install -r requirements.txt && python scripts/prefetch_model.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.embeddings import get_embedding_model  # noqa: E402

if __name__ == "__main__":
    get_embedding_model()
    print("Embedding model cached.")
