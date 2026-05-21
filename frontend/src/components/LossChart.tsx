// LossChart — a dependency-free inline-SVG metric chart for the run-detail page.
//
// Spec 06 §7 names recharts, but recharts is not yet a dependency; this
// minimal SVG sparkline carries the `run-detail-loss-chart` testid contract
// and renders a series of metric points. Swapping in recharts later is a
// drop-in behind the same testid.

export interface MetricPoint {
  step: number;
  value: number;
}

export interface LossChartProps {
  series: MetricPoint[];
  label?: string;
}

export function LossChart({ series, label = "metric" }: LossChartProps): JSX.Element {
  if (series.length === 0) {
    return (
      <div data-testid="run-detail-loss-chart">
        <p data-testid="run-detail-loss-chart-empty">No metrics yet.</p>
      </div>
    );
  }

  const width = 320;
  const height = 120;
  const values = series.map((p) => p.value);
  const max = Math.max(...values, 0);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const stepX = series.length > 1 ? width / (series.length - 1) : width;

  const points = series
    .map((p, i) => {
      const x = i * stepX;
      const y = height - ((p.value - min) / span) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div data-testid="run-detail-loss-chart">
      <svg width={width} height={height} role="img" aria-label={`${label} chart`}>
        <polyline
          points={points}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        />
      </svg>
      <p>
        {label}: latest {series[series.length - 1]?.value.toFixed(4)}
      </p>
    </div>
  );
}
