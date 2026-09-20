"""
Onboarding guide generation — POST /repos/{repo_id}/onboarding-guide.

Generation can take a few seconds (it's a real Groq call over a fair
chunk of material), so the frontend triggers it explicitly with a
button rather than fetching it automatically.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import OnboardingGuideResponse
from app.services.onboarding import generate_onboarding_guide
from app.services.qa import RepoNotIndexedError

router = APIRouter(prefix="/repos", tags=["onboarding"])


@router.post("/{repo_id}/onboarding-guide", response_model=OnboardingGuideResponse)
def create_onboarding_guide(repo_id: str) -> OnboardingGuideResponse:
    try:
        return generate_onboarding_guide(repo_id)
    except RepoNotIndexedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc
