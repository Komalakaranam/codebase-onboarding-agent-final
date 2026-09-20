/**
 * Thin wrapper around the FastAPI backend.
 *
 * Every function here does a plain `fetch()` call — there is no state,
 * caching, or magic. React components import these functions, call them
 * inside event handlers or effects, and manage loading/error state
 * themselves. This keeps the "talk to the backend" logic in one place
 * instead of scattered across components.
 *
 * The backend's CORS middleware (see backend/app/main.py) is what allows
 * this code — running on http://localhost:5173 during `npm run dev` — to
 * call a server on a different origin (http://127.0.0.1:8000) at all.
 * Without it, the browser would block every request below with a CORS error.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    // FastAPI's HTTPException responses look like { "detail": "..." }
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(detail);
  }

  return response.json();
}

/** POST /repos/index — clone, parse, embed, and store a repo in ChromaDB. */
export function indexRepo(repoUrl) {
  return request("/repos/index", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

/** POST /repos/{repo_id}/ask — retrieval (ChromaDB) + generation (Groq). */
export function askQuestion(repoId, question, topK = 5) {
  return request(`/repos/${encodeURIComponent(repoId)}/ask`, {
    method: "POST",
    body: JSON.stringify({ question, top_k: topK }),
  });
}

/** GET /repos/{repo_id}/history — past Q&A pairs, most recent first. */
export function getHistory(repoId, limit = 50) {
  return request(`/repos/${encodeURIComponent(repoId)}/history?limit=${limit}`);
}

/** GET /repos/{repo_id}/overview — stats + languages + LLM project summary. */
export function getOverview(repoId) {
  return request(`/repos/${encodeURIComponent(repoId)}/overview`);
}

/** POST /repos/{repo_id}/onboarding-guide — LLM-generated Markdown onboarding doc. */
export function generateOnboardingGuide(repoId) {
  return request(`/repos/${encodeURIComponent(repoId)}/onboarding-guide`, {
    method: "POST",
  });
}

/** POST /repos/{repo_id}/evaluate — runs test questions through /ask and checks retrieval accuracy. */
export function runEvaluation(repoId, questions) {
  return request(`/repos/${encodeURIComponent(repoId)}/evaluate`, {
    method: "POST",
    body: JSON.stringify({ questions }),
  });
}
