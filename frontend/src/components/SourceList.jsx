/** Renders an answer's source references as readable chips, not raw JSON. */
export default function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources">
      <div className="sources-title">Sources</div>
      <ul className="source-list">
        {sources.map((source, index) => (
          <li key={index} className="source-chip">
            <code className="source-path">
              {source.file_path}:{source.start_line}-{source.end_line}
            </code>
            {source.name && (
              <span className="source-symbol">
                <code>{source.name}</code>
              </span>
            )}
            <span className="source-score">{Math.round(source.relevance_score * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
