// Shared severity color system for the intel dashboard.
//
// Several panels independently reimplemented red/amber/green threshold logic
// (risk score, reliability index, divergence score, burst z-score, urgency).
// Centralizing it here means the same numeric severity always renders with the
// same color across every stage of the pipeline — reinforcing the causal chain
// visually (red event → red exploitation flag → red countermeasure urgency).

export const SEVERITY_COLORS = {
  critical: "#ef4444",
  warning: "#f59e0b",
  good: "#10b981",
  info: "#3b82f6",
  accent: "#8b5cf6",
  neutral: "#94a3b8",
} as const;

export type SeverityDirection = "higher-is-worse" | "higher-is-better";

interface SeverityScaleOptions {
  /** Value at/above which the metric is considered severe (or, for higher-is-better, healthy). Default 0.7 */
  high?: number;
  /** Value at/above which the metric is considered moderate. Default 0.4 */
  mid?: number;
  /** Whether a higher value means worse (e.g. risk score) or better (e.g. reliability index). Default "higher-is-worse" */
  direction?: SeverityDirection;
}

/** Maps a 0-1 (or any consistently-scaled) numeric score to a severity color. */
export function severityColor(value: number, opts: SeverityScaleOptions = {}): string {
  const { high = 0.7, mid = 0.4, direction = "higher-is-worse" } = opts;
  if (direction === "higher-is-better") {
    if (value >= high) return SEVERITY_COLORS.good;
    if (value >= mid) return SEVERITY_COLORS.warning;
    return SEVERITY_COLORS.critical;
  }
  if (value >= high) return SEVERITY_COLORS.critical;
  if (value >= mid) return SEVERITY_COLORS.warning;
  return SEVERITY_COLORS.good;
}

/** Maps an unbounded magnitude (e.g. burst z-score) to severity using explicit cut points. */
export function magnitudeSeverityColor(value: number | null | undefined, high = 6, mid = 4): string {
  if (value == null) return SEVERITY_COLORS.neutral;
  if (value >= high) return SEVERITY_COLORS.critical;
  if (value >= mid) return SEVERITY_COLORS.warning;
  return SEVERITY_COLORS.good;
}

export function severityLabel(value: number, opts: SeverityScaleOptions = {}): "critical" | "warning" | "good" {
  const { high = 0.7, mid = 0.4, direction = "higher-is-worse" } = opts;
  const severe = direction === "higher-is-worse" ? value >= high : value < mid;
  const moderate = direction === "higher-is-worse" ? value >= mid : value < high;
  if (severe) return "critical";
  if (moderate) return "warning";
  return "good";
}
