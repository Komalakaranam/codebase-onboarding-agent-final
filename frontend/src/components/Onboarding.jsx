import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { generateOnboardingGuide } from "../api";
import { ErrorIcon } from "./StatusIcons";

/**
 * On-demand onboarding guide: generation is a real Groq call over a
 * fair chunk of material (README + config files + retrieved key code
 * chunks — see backend/app/services/onboarding.py), so it's triggered
 * by a button rather than fetched automatically like Overview.
 */
export default function Onboarding({ repoId, repoName }) {
  const [guide, setGuide] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    setLoading(true);
    setError("");
    try {
      const result = await generateOnboardingGuide(repoId);
      setGuide(result);
    } catch (err) {
      setError(err.message || "Failed to generate onboarding guide.");
    } finally {
      setLoading(false);
    }
  }

  function handleDownload() {
    const blob = new Blob([guide.guide_markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${repoName.replace(/[/\\]/g, "_")}-onboarding-guide.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  return (
    <section className="card">
      <div className="history-header">
        <div>
          <h2>Onboarding Guide</h2>
          <p className="muted">
            An AI-generated guide covering the project overview, tech stack,
            structure, key components, and setup for {repoName}.
          </p>
        </div>
        <button className="btn" onClick={handleGenerate} disabled={loading}>
          {loading ? "Generating…" : guide ? "Regenerate Guide" : "Generate Guide"}
        </button>
      </div>

      {loading && (
        <div className="loading-note">
          <span className="spinner" />
          Reading the README, config files, and key code — this can take a
          bit longer than a chat answer.
        </div>
      )}

      {error && (
        <div className="status-box error">
          <ErrorIcon />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && !guide && (
        <p className="muted spaced-top">Click "Generate Guide" to create one.</p>
      )}

      {guide && (
        <>
          <div className="info-card">
            <div className="markdown">
              <ReactMarkdown>{guide.guide_markdown}</ReactMarkdown>
            </div>
          </div>
          <button className="btn btn-secondary spaced-top" onClick={handleDownload}>
            Download as Markdown
          </button>
        </>
      )}
    </section>
  );
}
