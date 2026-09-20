import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getHistory } from "../api";
import { formatUtcTimestamp } from "../utils";
import { ErrorIcon } from "./StatusIcons";

/**
 * Step 3 of the UI: past Q&A pairs for the current repo, most recent
 * first (the backend's SQL query already orders them — this component
 * just renders what GET /repos/{repo_id}/history returns).
 *
 * Note: history rows only store question + answer text (see
 * backend/app/database.py's ChatHistory model), not source references,
 * so past entries here don't show file/line citations — ask again in
 * the Chat tab to see those.
 */
export default function History({ repoId, repoName }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadHistory() {
    setLoading(true);
    setError("");
    try {
      const data = await getHistory(repoId);
      setEntries(data.history);
    } catch (err) {
      setError(err.message || "Failed to load history.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId]);

  return (
    <section className="card">
      <div className="history-header">
        <div>
          <h2>History for {repoName}</h2>
          <p className="muted">Past questions and answers, most recent first.</p>
        </div>
        <button className="btn btn-secondary" onClick={loadHistory} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="status-box error">
          <ErrorIcon />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && entries.length === 0 && (
        <p className="muted">No questions asked yet — try the Chat tab.</p>
      )}

      {loading && (
        <ul className="history-list" role="status" aria-label="Loading history">
          {[0, 1, 2].map((i) => (
            <li className="history-item" key={i}>
              <span className="skeleton skeleton-line" style={{ width: "120px" }} />
              <span className="skeleton skeleton-line" style={{ width: "65%" }} />
              <span className="skeleton skeleton-line skeleton-line-short" />
            </li>
          ))}
        </ul>
      )}

      <ul className="history-list">
        {!loading && entries.map((entry) => (
          <li key={entry.id} className="history-item">
            <div className="history-time">
              {formatUtcTimestamp(entry.created_at)}
            </div>
            <div className="history-question">Q: {entry.question}</div>
            <div className="history-answer markdown">
              <ReactMarkdown>{entry.answer}</ReactMarkdown>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
