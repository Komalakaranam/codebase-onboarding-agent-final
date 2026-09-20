import { useState } from "react";
import { runEvaluation } from "../api";
import { ErrorIcon } from "./StatusIcons";
import BarChart from "./BarChart";

const PLACEHOLDER = `How does retrieval find the right chunks? | app/services/vector_store.py
What does the /ask endpoint do? | app/routers/qa.py`;

/** Parses "question | expected_source" lines, skipping blanks and malformed lines. */
function parseQuestions(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const separatorIndex = line.indexOf("|");
      if (separatorIndex === -1) return null;
      const question = line.slice(0, separatorIndex).trim();
      const expectedSource = line.slice(separatorIndex + 1).trim();
      if (!question || !expectedSource) return null;
      return { question, expected_source: expectedSource };
    })
    .filter(Boolean);
}

export default function Evaluation({ repoId, repoName }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const questions = parseQuestions(text);

  async function handleRun() {
    setLoading(true);
    setError("");
    try {
      const data = await runEvaluation(repoId, questions);
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to run evaluation.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>Evaluation</h2>
      <p className="muted">
        Test retrieval accuracy for {repoName}. One test per line: a question,
        then <code>|</code>, then the file path it should retrieve (e.g.{" "}
        <code>services/qa.py</code> — include enough of the path to
        disambiguate same-named files in different folders).
      </p>

      <textarea
        className="text-input eval-textarea"
        placeholder={PLACEHOLDER}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={loading}
        rows={6}
      />

      <div className="field-row">
        <button className="btn" onClick={handleRun} disabled={loading || questions.length === 0}>
          {loading ? "Running…" : "Run Evaluation"}
        </button>
        <span className="muted">
          {questions.length} test{questions.length === 1 ? "" : "s"} parsed
        </span>
      </div>

      {loading && (
        <div className="loading-note">
          <span className="spinner" />
          Running each question through retrieval + generation — this takes
          roughly as long as asking them one by one in Chat.
        </div>
      )}

      {error && (
        <div className="status-box error">
          <ErrorIcon />
          <span>{error}</span>
        </div>
      )}

      {loading && !result && (
        <div className="skeleton-group spaced-top" role="status" aria-label="Running evaluation">
          <div className="stat-grid">
            <div className="stat-tile">
              <span className="skeleton skeleton-value" />
              <span className="skeleton skeleton-label" />
            </div>
            <div className="stat-tile">
              <span className="skeleton skeleton-value" />
              <span className="skeleton skeleton-label" />
            </div>
            <div className="stat-tile">
              <span className="skeleton skeleton-value" />
              <span className="skeleton skeleton-label" />
            </div>
            <div className="stat-tile">
              <span className="skeleton skeleton-value" />
              <span className="skeleton skeleton-label" />
            </div>
          </div>

          <div className="info-card">
            <span className="skeleton skeleton-line skeleton-line-title" />
            <span className="skeleton skeleton-line" />
            <span className="skeleton skeleton-line skeleton-line-short" />
          </div>
        </div>
      )}

      {result && (
        <>
          <div className="stat-grid spaced-top">
            <div className="stat-tile">
              <span className="stat-value">{result.total_questions}</span>
              <span className="stat-label">Test Questions</span>
            </div>
            <div className="stat-tile">
              <span className="stat-value">{result.top1_accuracy_percent}%</span>
              <span className="stat-label">Top-1 Accuracy</span>
            </div>
            <div className="stat-tile">
              <span className="stat-value">{result.top5_accuracy_percent}%</span>
              <span className="stat-label">Top-5 Accuracy</span>
            </div>
            <div className="stat-tile">
              <span className="stat-value">{Math.round(result.avg_response_time_ms)}ms</span>
              <span className="stat-label">Avg Response Time</span>
            </div>
          </div>

          <div className="info-card spaced-top">
            <div className="info-card-title">Response Time per Question</div>
            <BarChart
              data={result.results.map((row, i) => ({
                label: `Q${i + 1}`,
                value: row.response_time_ms,
                color: "var(--color-accent)",
              }))}
              valueFormatter={(v) => `${v}ms`}
            />
          </div>

          <div className="info-card spaced-top">
            <div className="info-card-title">Correct vs Incorrect</div>
            <BarChart
              data={[
                {
                  label: "Top-1 Correct",
                  value: result.results.filter((row) => row.correct_top1).length,
                  color: "var(--color-success-text)",
                },
                {
                  label: "Top-1 Incorrect",
                  value: result.results.filter((row) => !row.correct_top1).length,
                  color: "var(--color-error-text)",
                },
                {
                  label: "Top-5 Correct",
                  value: result.results.filter((row) => row.correct_top5).length,
                  color: "var(--color-success-text)",
                },
                {
                  label: "Top-5 Incorrect",
                  value: result.results.filter((row) => !row.correct_top5).length,
                  color: "var(--color-error-text)",
                },
              ]}
            />
          </div>

          <div className="table-wrap spaced-top">
            <table className="eval-table">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Expected</th>
                  <th>Retrieved</th>
                  <th>Top-1</th>
                  <th>Top-5</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((row, i) => (
                  <tr key={i}>
                    <td>{row.question}</td>
                    <td>
                      <code className="source-path">{row.expected_source}</code>
                    </td>
                    <td>
                      {row.retrieved_sources.map((path, j) => (
                        <code className="source-path eval-retrieved-path" key={j}>
                          {path}
                        </code>
                      ))}
                    </td>
                    <td className={row.correct_top1 ? "eval-correct" : "eval-incorrect"}>
                      {row.correct_top1 ? "Correct" : "Incorrect"}
                    </td>
                    <td className={row.correct_top5 ? "eval-correct" : "eval-incorrect"}>
                      {row.correct_top5 ? "Correct" : "Incorrect"}
                    </td>
                    <td>{row.response_time_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
