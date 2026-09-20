import { useRef, useState } from "react";
import { indexRepo } from "../api";
import { CheckIcon, ErrorIcon } from "./StatusIcons";
import IndexingSteps from "./IndexingSteps";

const INDEXING_STEPS = [
  { id: "clone", label: "Cloning repository" },
  { id: "parse", label: "Parsing code files" },
  { id: "embed", label: "Generating embeddings" },
  { id: "store", label: "Storing in vector database" },
];

const IDLE_STATUSES = Object.fromEntries(INDEXING_STEPS.map((s) => [s.id, "pending"]));

/** Which step actually failed, inferred from the backend's own error message
 *  (see backend/app/routers/repos.py — each stage raises a distinct wording). */
function classifyErrorStep(message) {
  if (message.includes("parsing failed")) return "parse";
  if (message.includes("embedding/storage failed")) return "embed";
  return "clone";
}

/**
 * Step 1 of the UI: paste a GitHub URL, trigger POST /repos/index,
 * and show progress → success (or error). On success, the parent App
 * gets the indexed repo's info via onIndexed() and switches to Overview.
 */
export default function RepoInput({ onIndexed }) {
  const [repoUrl, setRepoUrl] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [stepStatuses, setStepStatuses] = useState(IDLE_STATUSES);
  const timers = useRef([]);

  function clearTimers() {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = repoUrl.trim();
    if (!trimmed) return;

    setStatus("loading");
    setErrorMessage("");
    setStepStatuses({ ...IDLE_STATUSES, clone: "active" });

    timers.current.push(
      setTimeout(() => setStepStatuses((s) => ({ ...s, clone: "done", parse: "active" })), 900),
      setTimeout(() => setStepStatuses((s) => ({ ...s, parse: "done", embed: "active" })), 1800)
    );

    try {
      const data = await indexRepo(trimmed);
      clearTimers();
      setStepStatuses({ clone: "done", parse: "done", embed: "done", store: "done" });
      setResult(data);
      setStatus("success");
    } catch (err) {
      clearTimers();
      const message = err.message || "Failed to index repository.";
      const failedStep = classifyErrorStep(message);
      const failedIndex = INDEXING_STEPS.findIndex((s) => s.id === failedStep);
      setStepStatuses(
        Object.fromEntries(
          INDEXING_STEPS.map((s, i) => [
            s.id,
            i < failedIndex ? "done" : i === failedIndex ? "error" : "pending",
          ])
        )
      );
      setErrorMessage(message);
      setStatus("error");
    }
  }

  return (
    <section className="card">
      <div className="welcome-intro">
        <h1 className="welcome-headline">Understand any codebase instantly</h1>
        <p className="welcome-tagline">
          Paste a GitHub repo URL below and start asking questions about it in
          plain English.
        </p>
      </div>

      <p className="muted">
        The backend clones the repo, parses Python/JS files into chunks,
        embeds them, and stores the vectors in ChromaDB.
      </p>

      <form onSubmit={handleSubmit} className="field-row">
        <input
          type="text"
          className="text-input"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          disabled={status === "loading"}
        />
        <button
          type="submit"
          className="btn"
          disabled={status === "loading" || !repoUrl.trim()}
        >
          {status === "loading" ? "Indexing…" : "Index Repository"}
        </button>
      </form>

      {(status === "loading" || status === "error") && (
        <IndexingSteps steps={INDEXING_STEPS} statuses={stepStatuses} />
      )}

      {status === "error" && (
        <div className="status-box error">
          <ErrorIcon />
          <span>{errorMessage}</span>
        </div>
      )}

      {status === "success" && result && (
        <div className="success-panel">
          <p className="success-message">
            <CheckIcon />
            Indexed {result.repo_name} successfully
          </p>
          <div className="stat-grid">
            <div className="stat-tile">
              <span className="stat-value">{result.files_scanned}</span>
              <span className="stat-label">Files scanned</span>
            </div>
            <div className="stat-tile">
              <span className="stat-value">{result.chunks_found}</span>
              <span className="stat-label">Chunks found</span>
            </div>
            <div className="stat-tile">
              <span className="stat-value">{result.chunks_embedded}</span>
              <span className="stat-label">Chunks embedded</span>
            </div>
          </div>
          <button
            className="btn"
            onClick={() =>
              onIndexed({
                repoId: result.repo_id,
                repoName: result.repo_name,
              })
            }
          >
            Start Chatting →
          </button>
        </div>
      )}
    </section>
  );
}
