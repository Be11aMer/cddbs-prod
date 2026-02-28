import { Box, Typography, Stack, Tooltip } from "@mui/material";
import type { QualityDimension } from "../api";

interface QualityRadarChartProps {
  dimensions: Record<string, QualityDimension>;
}

const DIMENSION_LABELS: Record<string, string> = {
  structural_completeness: "Structure",
  attribution_quality: "Attribution",
  confidence_signaling: "Confidence",
  evidence_presentation: "Evidence",
  analytical_rigor: "Rigor",
  actionability: "Actionable",
  readability: "Readability",
};

const DIMENSION_COLORS: Record<string, string> = {
  structural_completeness: "#3b82f6",
  attribution_quality: "#8b5cf6",
  confidence_signaling: "#06b6d4",
  evidence_presentation: "#10b981",
  analytical_rigor: "#f59e0b",
  actionability: "#ef4444",
  readability: "#ec4899",
};

function getScoreColor(score: number, max: number): string {
  const pct = score / max;
  if (pct >= 0.8) return "#10b981";
  if (pct >= 0.6) return "#3b82f6";
  if (pct >= 0.4) return "#f59e0b";
  return "#ef4444";
}

export const QualityRadarChart = ({ dimensions }: QualityRadarChartProps) => {
  const entries = Object.entries(dimensions);
  const numAxes = entries.length;
  if (numAxes === 0) return null;

  const cx = 100;
  const cy = 100;
  const maxRadius = 75;
  const angleStep = (2 * Math.PI) / numAxes;

  // Build polygon points for the data
  const dataPoints = entries.map(([, dim], i) => {
    const angle = angleStep * i - Math.PI / 2; // Start from top
    const r = (dim.score / dim.max) * maxRadius;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  });

  const dataPolygon = dataPoints.map((p) => `${p.x},${p.y}`).join(" ");

  // Grid rings at 25%, 50%, 75%, 100%
  const rings = [0.25, 0.5, 0.75, 1.0];

  // Axis lines and labels
  const axes = entries.map(([key], i) => {
    const angle = angleStep * i - Math.PI / 2;
    const endX = cx + maxRadius * Math.cos(angle);
    const endY = cy + maxRadius * Math.sin(angle);
    const labelX = cx + (maxRadius + 18) * Math.cos(angle);
    const labelY = cy + (maxRadius + 18) * Math.sin(angle);
    return { key, endX, endY, labelX, labelY };
  });

  return (
    <Box>
      <Typography variant="overline" color="text.secondary" fontWeight={700} sx={{ display: "block", mb: 1 }}>
        Quality Dimensions
      </Typography>

      <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
        <svg width="220" height="220" viewBox="0 0 200 200">
          {/* Grid rings */}
          {rings.map((pct) => {
            const points = entries.map((_, i) => {
              const angle = angleStep * i - Math.PI / 2;
              const r = pct * maxRadius;
              return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
            });
            return (
              <polygon
                key={pct}
                points={points.join(" ")}
                fill="none"
                stroke="rgba(148,163,184,0.15)"
                strokeWidth="0.5"
              />
            );
          })}

          {/* Axis lines */}
          {axes.map((a) => (
            <line
              key={a.key}
              x1={cx}
              y1={cy}
              x2={a.endX}
              y2={a.endY}
              stroke="rgba(148,163,184,0.1)"
              strokeWidth="0.5"
            />
          ))}

          {/* Data polygon */}
          <polygon
            points={dataPolygon}
            fill="rgba(59, 130, 246, 0.15)"
            stroke="#3b82f6"
            strokeWidth="1.5"
          />

          {/* Data points */}
          {dataPoints.map((p, i) => {
            const [, dim] = entries[i];
            return (
              <circle
                key={i}
                cx={p.x}
                cy={p.y}
                r="3"
                fill={getScoreColor(dim.score, dim.max)}
                stroke="#020617"
                strokeWidth="1"
              />
            );
          })}

          {/* Axis labels */}
          {axes.map((a) => (
            <text
              key={a.key}
              x={a.labelX}
              y={a.labelY}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgba(148,163,184,0.7)"
              fontSize="7"
              fontWeight="600"
            >
              {DIMENSION_LABELS[a.key] || a.key}
            </text>
          ))}
        </svg>
      </Box>

      {/* Dimension breakdown list */}
      <Stack spacing={1}>
        {entries.map(([key, dim]) => {
          const pct = Math.round((dim.score / dim.max) * 100);
          const color = DIMENSION_COLORS[key] || "#3b82f6";
          return (
            <Tooltip
              key={key}
              title={
                dim.issues.length > 0
                  ? dim.issues.map((issue, i) => (
                      <Typography key={i} variant="caption" display="block" sx={{ mb: 0.3 }}>
                        {issue}
                      </Typography>
                    ))
                  : "No issues found"
              }
              placement="left"
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    backgroundColor: color,
                    flexShrink: 0,
                  }}
                />
                <Typography variant="caption" sx={{ flex: 1, fontWeight: 600, fontSize: "0.7rem" }}>
                  {DIMENSION_LABELS[key] || key}
                </Typography>
                <Box
                  sx={{
                    flex: 2,
                    height: 4,
                    borderRadius: 2,
                    backgroundColor: "rgba(148,163,184,0.1)",
                    overflow: "hidden",
                  }}
                >
                  <Box
                    sx={{
                      height: "100%",
                      width: `${pct}%`,
                      borderRadius: 2,
                      backgroundColor: getScoreColor(dim.score, dim.max),
                      transition: "width 0.6s ease-out",
                    }}
                  />
                </Box>
                <Typography
                  variant="caption"
                  sx={{
                    width: 30,
                    textAlign: "right",
                    fontWeight: 700,
                    fontSize: "0.7rem",
                    color: getScoreColor(dim.score, dim.max),
                  }}
                >
                  {dim.score}/{dim.max}
                </Typography>
              </Box>
            </Tooltip>
          );
        })}
      </Stack>
    </Box>
  );
};
