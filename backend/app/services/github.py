"""
GitHub repository cloning service.

Step 1 of RAG pipeline: get the source code onto our machine so we can read it.
We use GitPython, which wraps the `git` CLI — so Git must be installed locally.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError

from app.config import settings


class GitHubCloneError(Exception):
    """Raised when a repo URL is invalid or cloning fails."""


def parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    """
    Extract owner and repo name from common GitHub URL formats.

    Supported examples:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - git@github.com:owner/repo.git
    """
    url = repo_url.strip().rstrip("/")

    # SSH form: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group("owner"), ssh_match.group("repo")

    parsed = urlparse(url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        raise GitHubCloneError("Only github.com URLs are supported in step 1.")

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise GitHubCloneError("URL must look like https://github.com/owner/repo")

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    return owner, repo


def build_clone_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}.git"


def get_repo_local_path(owner: str, repo: str) -> Path:
    """Each repo gets its own folder under backend/data/."""
    return settings.data_dir / f"{owner}__{repo}"


def clone_github_repo(repo_url: str, *, force_refresh: bool = False) -> tuple[Path, str, str]:
    """
    Clone (or re-use) a public GitHub repository.

    Returns:
        (local_path, owner, repo_name)
    """
    owner, repo_name = parse_github_repo_url(repo_url)
    local_path = get_repo_local_path(owner, repo_name)
    clone_url = build_clone_url(owner, repo_name)

    if local_path.exists():
        if force_refresh:
            shutil.rmtree(local_path)
        else:
            # Already cloned — skip network call (useful during development)
            return local_path, owner, repo_name

    local_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # depth=1 keeps the clone fast by fetching only the latest commit
        Repo.clone_from(clone_url, local_path, depth=1)
    except GitCommandError as exc:
        raise GitHubCloneError(
            f"Failed to clone {clone_url}. Is the repo public and the URL correct? "
            f"Details: {exc}"
        ) from exc

    return local_path, owner, repo_name


def list_code_files(repo_root: Path) -> list[Path]:
    """
    Walk the cloned repo and collect supported source files.

    We skip vendor/build folders so embeddings focus on project code.
    """
    files: list[Path] = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue

        # Skip hidden files like .env (shouldn't be in git, but be safe)
        if any(part.startswith(".") and part not in {".github"} for part in path.parts):
            continue

        if any(skip in path.parts for skip in settings.skip_dirs):
            continue

        if path.suffix.lower() in settings.supported_extensions:
            files.append(path)

    return sorted(files)
