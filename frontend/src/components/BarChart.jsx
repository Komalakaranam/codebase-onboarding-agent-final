/**
 * Plain horizontal bar chart — no charting library. Rows carry their
 * own label directly beside the bar (direct-labeled per the dataviz
 * skill, rather than relying on color alone for identity), with the
 * value shown at the end of each bar. A native <title> gives a basic
 * hover affordance without a custom tooltip layer.
 */
export default function BarChart({ data, valueFormatter = (v) => v }) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="bar-chart">
      {data.map((d, i) => (
        <div className="bar-chart-row" key={i}>
          <div className="bar-chart-label" title={d.label}>
            {d.label}
          </div>
          <div className="bar-chart-track">
            <div
              className="bar-chart-fill"
              style={{ width: `${(d.value / max) * 100}%`, background: d.color }}
              title={`${d.label}: ${valueFormatter(d.value)}`}
            />
          </div>
          <div className="bar-chart-value">{valueFormatter(d.value)}</div>
        </div>
      ))}
    </div>
  );
}
