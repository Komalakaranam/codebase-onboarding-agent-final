import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getOverview } from "../api";
import { ErrorIcon } from "./StatusIcons";
import DonutChart from "./DonutChart";

// Fixed hue assignment by language identity (never by position/index), so
// a language keeps the same color across repos with different language
// mixes. Colors are the dataviz-skill-validated categorical series in
// index.css. Anything outside this map falls back to the muted neutral.
const LANGUAGE_COLORS = {
  JavaScript: "var(--chart-series-1)",
  Python: "var(--chart-series-2)",
  TypeScript: "var(--chart-series-3)",
};
const FALLBACK_COLOR = "var(--color-muted)";

/**
 * Default landing view after indexing. Files/chunks/languages come
 * straight from disk + ChromaDB (fast); the description is a short
 * Groq-generated summary — see backend/app/services/overview.py.
 */
export default function Overview({ repoId, repoName }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadOverview() {
    setLoading(true);
    setError("");
    try {
      const result = await getOverview(repoId);
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to load overview.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOverview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId]);

  return (
    <section className="card">
      <h2>Overview</h2>
      <p className="muted">{repoName}</p>

      {loading && (
        <div className="skeleton-group" role="status" aria-label="Loading overview">
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
          </div>

          <div className="info-card">
            <span className="skeleton skeleton-line skeleton-line-title" />
            <div className="chart-card">
              <span className="skeleton skeleton-donut" />
              <div className="chart-legend">
                <span className="skeleton skeleton-line" style={{ width: "90px" }} />
                <span className="skeleton skeleton-line" style={{ width: "70px" }} />
              </div>
            </div>
          </div>

          <div className="info-card">
            <span className="skeleton skeleton-line skeleton-line-title" />
            <span className="skeleton skeleton-line" />
            <span className="skeleton skeleton-line" />
            <span className="skeleton skeleton-line skeleton-line-short" />
          </div>
        </div>
      )}

      {error && (
        <div className="status-box error">
          <ErrorIcon />
          <span>{error}</span>
        </div>
      )}

      {data && (
        <>
          <div className="stat-grid">
            <div className="stat-tile">
              <span className="stat-value">{data.files_scanned}</span>
              <span className="stat-label">Files</span>
            </div>
            <div className="stat-tile">
              <span className="stat-value">{data.chunks_found}</span>
              <span className="stat-label">Chunks</span>
            </div>
            <div className="stat-tile">
              <span className="stat-value stat-value-text">
                {data.languages.length > 0 ? data.languages.join(", ") : "—"}
              </span>
              <span className="stat-label">Languages</span>
            </div>
          </div>

          {Object.keys(data.language_breakdown).length > 0 && (
            <div className="info-card">
              <div className="info-card-title">Language Distribution</div>
              <div className="chart-card">
                <DonutChart
                  data={Object.entries(data.language_breakdown).map(([label, value]) => ({
                    label,
                    value,
                    color: LANGUAGE_COLORS[label] || FALLBACK_COLOR,
                  }))}
                />
                <div className="chart-legend">
                  {Object.entries(data.language_breakdown).map(([label, value]) => (
                    <div className="chart-legend-row" key={label}>
                      <span
                        className="chart-legend-swatch"
                        style={{ background: LANGUAGE_COLORS[label] || FALLBACK_COLOR }}
                      />
                      <span>{label}</span>
                      <span className="chart-legend-value">
                        {Math.round((value / data.files_scanned) * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="info-card">
            <div className="info-card-title">Project Info</div>
            <div className="markdown">
              <ReactMarkdown>{data.description}</ReactMarkdown>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
