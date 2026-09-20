/**
 * Plain-SVG donut chart — no charting library, so colors are exactly
 * what we pass in (never a library's default rainbow). Segments use
 * the stroke-dasharray/-dashoffset technique: each series is drawn as
 * an arc of a circle, offset by the cumulative length of the ones
 * before it, with a small gap between segments (dataviz skill's mark
 * spec) once there's more than one series.
 */
export default function DonutChart({ data, size = 140, strokeWidth = 26 }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const gap = data.length > 1 ? 3 : 0;

  let cumulative = 0;
  const segments = data.map((d) => {
    const rawLength = total > 0 ? (d.value / total) * circumference : 0;
    const visibleLength = Math.max(rawLength - gap, 0);
    const segment = {
      ...d,
      dasharray: `${visibleLength} ${circumference - visibleLength}`,
      dashoffset: -cumulative,
    };
    cumulative += rawLength;
    return segment;
  });

  return (
    <div className="donut-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {total === 0 ? (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="var(--color-border)"
              strokeWidth={strokeWidth}
            />
          ) : (
            segments.map((s) => (
              <circle
                key={s.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={s.color}
                strokeWidth={strokeWidth}
                strokeDasharray={s.dasharray}
                strokeDashoffset={s.dashoffset}
              >
                <title>
                  {s.label}: {total > 0 ? Math.round((s.value / total) * 100) : 0}%
                </title>
              </circle>
            ))
          )}
        </g>
      </svg>
      <div className="donut-center">
        <span className="donut-center-value">{total}</span>
        <span className="donut-center-label">files</span>
      </div>
    </div>
  );
}
