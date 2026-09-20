"""
Evaluation service — backs the Evaluation tab.

Runs a batch of test questions through the existing /ask pipeline
(answer_question — the same retrieval + generation used by Chat) and
checks whether each expected source file actually turned up in the
sources the pipeline retrieved. This measures *retrieval* quality
directly: if the right file never surfaces in `sources`, the LLM had
no chance of grounding its answer in it, regardless of how the answer
reads.

Two metrics are reported per question and in aggregate:
  - top-1: the expected source was the single highest-ranked result
    (the strict bar — what the pipeline would actually cite first).
  - top-5: the expected source appeared anywhere in the top-k results
    (the lenient bar — did retrieval have a chance at all).
"""

from __future__ import annotations

import time
from pathlib import PurePosixPath

from app.models.schemas import EvalQuestionResult, EvalRequest, EvalResponse
from app.services.qa import answer_question


def _is_correct(expected_source: str, retrieved_sources: list[str]) -> bool:
    """
    True if expected_source matches a retrieved path exactly, or as a
    path-segment-aligned suffix — e.g. "qa.py" matches ".../services/qa.py"
    but not ".../services/fastqa.py", and "services/qa.py" matches only
    that directory, not ".../routers/qa.py".

    Plain substring containment (the old `expected_source in path` check)
    let unrelated paths match on overlapping characters alone — e.g.
    "history.py" would also match a hypothetical "chat_history.py", and a
    bare "qa.py" couldn't distinguish "routers/qa.py" from "services/qa.py"
    beyond coincidence. Comparing whole path segments fixes the character-
    overlap case; a same-named file in two directories is still only
    disambiguated by giving enough of the path (e.g. "services/qa.py").
    """
    expected_parts = PurePosixPath(expected_source.strip("/")).parts
    if not expected_parts:
        return False
    for path in retrieved_sources:
        path_parts = PurePosixPath(path).parts
        if len(expected_parts) <= len(path_parts) and path_parts[-len(expected_parts):] == expected_parts:
            return True
    return False


def run_evaluation(repo_id: str, request: EvalRequest) -> EvalResponse:
    results: list[EvalQuestionResult] = []

    for item in request.questions:
        start = time.monotonic()
        response = answer_question(repo_id, item.question)
        elapsed_ms = (time.monotonic() - start) * 1000

        retrieved_sources = [source.file_path for source in response.sources]
        results.append(
            EvalQuestionResult(
                question=item.question,
                expected_source=item.expected_source,
                retrieved_sources=retrieved_sources,
                # Top-1 reuses the same segment-matching logic, scoped to
                # just the highest-ranked result — a strictly harder bar
                # than "anywhere in the top-k".
                correct_top1=_is_correct(item.expected_source, retrieved_sources[:1]),
                correct_top5=_is_correct(item.expected_source, retrieved_sources),
                response_time_ms=round(elapsed_ms),
            )
        )

    total = len(results)
    top1_count = sum(1 for r in results if r.correct_top1)
    top5_count = sum(1 for r in results if r.correct_top5)
    top1_accuracy_percent = round((top1_count / total) * 100, 1) if total else 0.0
    top5_accuracy_percent = round((top5_count / total) * 100, 1) if total else 0.0
    avg_response_time_ms = round(sum(r.response_time_ms for r in results) / total, 1) if total else 0.0

    return EvalResponse(
        repo_id=repo_id,
        results=results,
        total_questions=total,
        top1_accuracy_percent=top1_accuracy_percent,
        top5_accuracy_percent=top5_accuracy_percent,
        avg_response_time_ms=avg_response_time_ms,
    )
