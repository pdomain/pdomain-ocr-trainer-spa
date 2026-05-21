// EvalMetricsTable — renders overall metrics + glyph-feature slices (spec 07 §6.2).
//
// Slices are sorted by |delta_cer| descending; low-support rows are greyed.
// SPA-LOCAL: spec 07 §4 names a pd-ui component, but pd-ui does not export an
// EvalMetricsTable yet — this carries the spec-13 testid contract and is
// drop-in-replaceable once pd-ui ships one.

import type { EvalMetrics, EvalSlice } from "../api/eval";

interface Props {
  overall: EvalMetrics;
  slices: EvalSlice[];
}

function fmt(value: number | null | undefined): string {
  return value == null ? "—" : value.toFixed(4);
}

const OVERALL_FIELDS: Array<[keyof EvalMetrics, string]> = [
  ["cer", "CER"],
  ["wer", "WER"],
  ["exact_match_rate", "Exact match"],
  ["precision", "Precision"],
  ["recall", "Recall"],
  ["f1", "F1"],
  ["iou_50", "IoU@50"],
  ["iou_50_95", "IoU@50-95"],
  ["accuracy", "Accuracy"],
  ["f1_macro", "F1 macro"],
];

export function EvalMetricsTable({ overall, slices }: Props): JSX.Element {
  const sorted = [...slices].sort(
    (a, b) => Math.abs(b.delta_cer ?? 0) - Math.abs(a.delta_cer ?? 0),
  );

  return (
    <div data-testid="eval-metrics-table">
      <table data-testid="eval-metrics-overall">
        <tbody>
          {OVERALL_FIELDS.filter(([k]) => overall[k] != null).map(
            ([key, label]) => (
              <tr key={key}>
                <th>{label}</th>
                <td
                  data-testid={
                    key === "cer"
                      ? "eval-result-overall-cer"
                      : key === "wer"
                        ? "eval-result-overall-wer"
                        : `eval-result-overall-${key}`
                  }
                >
                  {fmt(overall[key] as number | null)}
                </td>
              </tr>
            ),
          )}
        </tbody>
      </table>

      {sorted.length > 0 && (
        <table data-testid="eval-metrics-slices">
          <thead>
            <tr>
              <th>Feature</th>
              <th>N pos</th>
              <th>N neg</th>
              <th>CER pos</th>
              <th>CER neg</th>
              <th>Δ CER</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr
                key={s.feature}
                data-testid={`eval-result-slice-${s.feature}`}
                style={s.low_support ? { color: "#999" } : undefined}
              >
                <td>
                  {s.feature}
                  {s.low_support ? " (low support)" : ""}
                </td>
                <td>{s.n_pos}</td>
                <td>{s.n_neg}</td>
                <td>{fmt(s.cer_pos)}</td>
                <td>{fmt(s.cer_neg)}</td>
                <td>
                  {s.delta_cer == null
                    ? "—"
                    : `${s.delta_cer >= 0 ? "+" : ""}${s.delta_cer.toFixed(4)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
