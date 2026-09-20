"""
Pydantic models define the shape of API requests and responses.

FastAPI uses these for automatic validation and OpenAPI docs.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class IndexStatus(str, Enum):
    """Lifecycle of a repo indexing job."""

    pending = "pending"
    cloning = "cloning"
    parsing = "parsing"
    embedding = "embedding"
    completed = "completed"
    failed = "failed"


class IndexRepoRequest(BaseModel):
    """Body sent when a user submits a GitHub repo URL."""

    repo_url: HttpUrl = Field(
        ...,
        description="Public GitHub repository URL, e.g. https://github.com/user/repo",
        examples=["https://github.com/tiangolo/fastapi"],
    )


class ParsedChunkPreview(BaseModel):
    """
    One logical unit of code extracted from a file.

    In step 2 we'll refine chunking; for step 1 this shows what the parser found.
    """

    file_path: str
    chunk_type: str  # e.g. "function", "class", "module"
    name: str | None = None
    start_line: int
    end_line: int
    content_preview: str  # First ~200 chars so responses stay small


class IndexRepoResponse(BaseModel):
    """Returned after cloning, parsing, and embedding a repository."""

    repo_id: str
    repo_url: str
    repo_name: str
    local_path: str
    status: IndexStatus
    files_scanned: int
    chunks_found: int
    chunks_embedded: int
    embedding_model: str
    chunks: list[ParsedChunkPreview]
    indexed_at: datetime
    message: str


class AskQuestionRequest(BaseModel):
    """Body sent when a user asks a natural-language question about a repo."""

    question: str = Field(
        ...,
        min_length=3,
        description="Natural-language question about the indexed codebase.",
        examples=["How does user authentication work in this repo?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="How many code chunks to retrieve from ChromaDB as context.",
    )


class SourceReference(BaseModel):
    """Points back to the exact code the answer was generated from."""

    file_path: str
    chunk_type: str  # "function", "class", "method", "module"
    name: str | None = None
    start_line: int
    end_line: int
    relevance_score: float = Field(
        ..., description="0-1 similarity score from ChromaDB; higher = more relevant."
    )


class AskQuestionResponse(BaseModel):
    """Returned after retrieval (ChromaDB) + generation (Groq LLM)."""

    repo_id: str
    question: str
    answer: str
    sources: list[SourceReference]
    model: str
    chunks_retrieved: int


class ChatHistoryEntry(BaseModel):
    """One saved Q&A pair, as stored in the SQLite chat_history table."""

    model_config = {"from_attributes": True}

    id: int
    repo_id: str
    question: str
    answer: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Returned by GET /repos/{repo_id}/history."""

    repo_id: str
    count: int
    history: list[ChatHistoryEntry]


class RepoOverviewResponse(BaseModel):
    """Returned by GET /repos/{repo_id}/overview."""

    repo_id: str
    files_scanned: int
    chunks_found: int
    languages: list[str]
    language_breakdown: dict[str, int] = Field(
        ..., description="File count per detected language, for the language distribution chart."
    )
    description: str


class OnboardingGuideResponse(BaseModel):
    """Returned by POST /repos/{repo_id}/onboarding-guide."""

    repo_id: str
    guide_markdown: str
    generated_at: datetime


class EvalQuestion(BaseModel):
    """One test case: a question plus the source file the answer should cite."""

    question: str = Field(..., min_length=3)
    expected_source: str = Field(
        ...,
        min_length=1,
        description=(
            "File path (or trailing path segments, e.g. 'services/qa.py') "
            "expected among the retrieved sources. Matched on whole path "
            "segments, not raw substring — a bare filename like 'qa.py' "
            "still matches any directory containing that file, so include "
            "enough of the path to disambiguate same-named files."
        ),
    )


class EvalRequest(BaseModel):
    """Body sent to POST /repos/{repo_id}/evaluate."""

    questions: list[EvalQuestion] = Field(..., min_length=1)


class EvalQuestionResult(BaseModel):
    question: str
    expected_source: str
    retrieved_sources: list[str]
    correct_top1: bool = Field(
        ..., description="Whether expected_source matched retrieved_sources[0] specifically."
    )
    correct_top5: bool = Field(
        ..., description="Whether expected_source matched anywhere in retrieved_sources."
    )
    response_time_ms: int


class EvalResponse(BaseModel):
    """Returned by POST /repos/{repo_id}/evaluate."""

    repo_id: str
    results: list[EvalQuestionResult]
    total_questions: int
    top1_accuracy_percent: float = Field(
        ..., description="Percent of questions where the expected source was ranked first."
    )
    top5_accuracy_percent: float = Field(
        ..., description="Percent of questions where the expected source appeared anywhere in the top-k."
    )
    avg_response_time_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
