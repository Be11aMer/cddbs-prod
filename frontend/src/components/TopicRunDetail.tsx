import {
  Box,
  Typography,
  Chip,
  LinearProgress,
  Paper,
  Divider,
  Collapse,
  IconButton,
  Tooltip,
  Link,
  CircularProgress,
  Alert,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import VerifiedIcon from "@mui/icons-material/Verified";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ReportProblemIcon from "@mui/icons-material/ReportProblem";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useQuery } from "@tanstack/react-query";
import { fetchTopicRun, type TopicOutletResult, type CoordinationDetail } from "../api";
import { useState } from "react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getDivergenceColor(score: number | null): string {
  if (score === null) return "#94a3b8";
  if (score >= 70) return "#ef4444";
  if (score >= 45) return "#f59e0b";
  if (score >= 20) return "#3b82f6";
  return "#10b981";
}

function getDivergenceLabel(score: number | null): string {
  if (score === null) return "PENDING";
  if (score >= 70) return "HIGH DIVERGENCE";
  if (score >= 45) return "ELEVATED";
  if (score >= 20) return "MODERATE";
  return "ALIGNED";
}

function getAmplificationColor(signal: string | null): string {
  if (signal === "high") return "#ef4444";
  if (signal === "medium") return "#f59e0b";
  return "#10b981";
}

// ---------------------------------------------------------------------------
// Coordination banner
// ---------------------------------------------------------------------------

function CoordinationBanner({
  signal,
  detail,
}: {
  signal: number;
  detail: CoordinationDetail | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round(signal * 100);
  const isHigh = signal >= 0.5;
  const color = isHigh ? "#ef4444" : signal >= 0.25 ? "#f59e0b" : "#3b82f6";
  const label = isHigh ? "HIGH COORDINATION RISK" : signal >= 0.25 ? "MODERATE COORDINATION RISK" : "LOW COORDINATION SIGNAL";

  return (
    <Paper
      sx={{
        border: `1px solid ${color}33`,
        backgroundColor: `${color}08`,
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.25,
          cursor: detail ? "pointer" : "default",
          "&:hover": detail ? { backgroundColor: `${color}06` } : {},
        }}
        onClick={() => detail && setExpanded((e) => !e)}
      >
        <ReportProblemIcon sx={{ fontSize: 16, color, flexShrink: 0 }} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography variant="caption" fontWeight={800} sx={{ fontSize: "0.72rem", color, letterSpacing: "0.04em" }}>
              {label}
            </Typography>
            <Chip
              label={`${pct}%`}
              size="small"
              sx={{
                height: 16, fontSize: "0.6rem", fontWeight: 800,
                backgroundColor: `${color}18`, color,
                border: `1px solid ${color}33`,
                "& .MuiChip-label": { px: 0.75 },
              }}
            />
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
            {detail
              ? `${detail.coordinated_outlets.length} of ${detail.total_outlet_count} outlets share narrative techniques — potential coordinated messaging`
              : "No significant coordination detected across high-divergence outlets"}
          </Typography>
        </Box>
        {detail && (
          <IconButton size="small" sx={{ p: 0.25, color }}>
            {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        )}
      </Box>

      {detail && (
        <Collapse in={expanded}>
          <Divider sx={{ borderColor: `${color}18` }} />
          <Box sx={{ px: 2, py: 1.25 }}>
            <Typography variant="caption" fontWeight={700} color="text.disabled" sx={{ fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Shared Techniques
            </Typography>
            <Box sx={{ mt: 0.5, mb: 1.25, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {detail.shared_techniques.map((t, i) => (
                <Chip
                  key={i}
                  label={t}
                  size="small"
                  sx={{
                    height: 18, fontSize: "0.62rem", fontWeight: 600,
                    backgroundColor: `${color}12`, color,
                    border: `1px solid ${color}28`,
                    "& .MuiChip-label": { px: 0.75 },
                  }}
                />
              ))}
            </Box>
            <Typography variant="caption" fontWeight={700} color="text.disabled" sx={{ fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Coordinated Outlets
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.72rem", display: "block", mt: 0.5 }}>
              {detail.coordinated_outlets.join(" · ")}
            </Typography>
          </Box>
        </Collapse>
      )}
    </Paper>
  );
}


// ---------------------------------------------------------------------------
// Outlet card
// ---------------------------------------------------------------------------

function OutletCard({ result }: { result: TopicOutletResult }) {
  const [expanded, setExpanded] = useState(false);
  const color = getDivergenceColor(result.divergence_score);
  const ampColor = getAmplificationColor(result.amplification_signal);
  const pct = result.divergence_score ?? 0;

  return (
    <Paper
      sx={{
        border: `1px solid ${color}33`,
        backgroundColor: `${color}08`,
        borderRadius: 2,
        overflow: "hidden",
        transition: "box-shadow 0.2s ease",
        "&:hover": { boxShadow: `0 0 16px ${color}22` },
      }}
    >
      {/* Card header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.5 }}>
        {/* Domain */}
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="subtitle2" fontWeight={800} sx={{ fontSize: "0.85rem" }}>
            {result.outlet_domain || result.outlet_name}
          </Typography>
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.65rem" }}>
            {result.articles_analyzed} article{result.articles_analyzed !== 1 ? "s" : ""} analysed
          </Typography>
        </Box>

        {/* Amplification badge */}
        {result.amplification_signal && (
          <Chip
            label={`AMP: ${result.amplification_signal.toUpperCase()}`}
            size="small"
            sx={{
              height: 18, fontSize: "0.6rem", fontWeight: 800, letterSpacing: "0.04em",
              backgroundColor: `${ampColor}18`, color: ampColor,
              border: `1px solid ${ampColor}33`,
              "& .MuiChip-label": { px: 0.75 },
            }}
          />
        )}

        {/* Divergence score badge */}
        <Box sx={{ textAlign: "right", flexShrink: 0, minWidth: 52 }}>
          <Typography variant="h6" fontWeight={900} sx={{ color, lineHeight: 1, fontSize: "1.25rem" }}>
            {result.divergence_score ?? "—"}
          </Typography>
          <Typography variant="caption" sx={{ color, fontSize: "0.58rem", fontWeight: 700, letterSpacing: "0.03em" }}>
            {getDivergenceLabel(result.divergence_score)}
          </Typography>
        </Box>
      </Box>

      {/* Divergence bar */}
      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{
          height: 3, mx: 0,
          backgroundColor: "rgba(255,255,255,0.05)",
          "& .MuiLinearProgress-bar": { backgroundColor: color },
        }}
      />

      {/* Framing summary */}
      {result.framing_summary && (
        <Box sx={{ px: 2, pt: 1.25, pb: expanded ? 0.5 : 1.5 }}>
          <Typography variant="body2" sx={{ fontSize: "0.8rem", lineHeight: 1.5, color: "text.secondary" }}>
            {result.framing_summary}
          </Typography>
        </Box>
      )}

      {/* Propaganda techniques */}
      {result.propaganda_techniques && result.propaganda_techniques.length > 0 && (
        <Box sx={{ px: 2, pb: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
          {result.propaganda_techniques.map((t, i) => (
            <Chip
              key={i}
              label={t}
              size="small"
              icon={<WarningAmberIcon sx={{ fontSize: "12px !important" }} />}
              sx={{
                height: 18, fontSize: "0.62rem", fontWeight: 600,
                backgroundColor: "rgba(245,158,11,0.1)", color: "#f59e0b",
                border: "1px solid rgba(245,158,11,0.2)",
                "& .MuiChip-label": { pl: 0.25, pr: 0.75 },
              }}
            />
          ))}
        </Box>
      )}

      {/* Expandable detail */}
      {(result.divergence_explanation || result.key_claims?.length || result.omissions?.length || result.article_links?.length) && (
        <>
          <Box
            sx={{
              display: "flex", alignItems: "center", px: 2, py: 0.5,
              borderTop: "1px solid rgba(148,163,184,0.07)",
              cursor: "pointer", "&:hover": { backgroundColor: "rgba(255,255,255,0.02)" },
            }}
            onClick={() => setExpanded((e) => !e)}
          >
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem", flexGrow: 1 }}>
              {expanded ? "Hide details" : "Show analyst notes & sources"}
            </Typography>
            <IconButton size="small" sx={{ p: 0.25 }}>
              {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          </Box>

          <Collapse in={expanded}>
            <Box sx={{ px: 2, pb: 1.5, display: "flex", flexDirection: "column", gap: 1.5 }}>
              {result.divergence_explanation && (
                <Box>
                  <Typography variant="caption" fontWeight={700} color="text.disabled" sx={{ fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Analyst Notes
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5, fontSize: "0.78rem", lineHeight: 1.55, color: "text.secondary" }}>
                    {result.divergence_explanation}
                  </Typography>
                </Box>
              )}

              {/* Key claims made by this outlet (not in neutral baseline) */}
              {result.key_claims && result.key_claims.length > 0 && (
                <Box>
                  <Typography variant="caption" fontWeight={700} color="text.disabled" sx={{ fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Key Claims by Outlet
                  </Typography>
                  <Box component="ul" sx={{ mt: 0.5, mb: 0, pl: 2, display: "flex", flexDirection: "column", gap: 0.3 }}>
                    {result.key_claims.map((claim, i) => (
                      <Box component="li" key={i}>
                        <Typography variant="caption" sx={{ fontSize: "0.74rem", color: "text.secondary", lineHeight: 1.5 }}>
                          {claim}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}

              {/* Facts omitted vs. neutral baseline */}
              {result.omissions && result.omissions.length > 0 && (
                <Box>
                  <Typography variant="caption" fontWeight={700} sx={{ fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "#f59e0b" }}>
                    Baseline Facts Omitted
                  </Typography>
                  <Box component="ul" sx={{ mt: 0.5, mb: 0, pl: 2, display: "flex", flexDirection: "column", gap: 0.3 }}>
                    {result.omissions.map((omission, i) => (
                      <Box component="li" key={i}>
                        <Typography variant="caption" sx={{ fontSize: "0.74rem", color: "#d97706", lineHeight: 1.5 }}>
                          {omission}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}

              {result.article_links && result.article_links.length > 0 && (
                <Box>
                  <Typography variant="caption" fontWeight={700} color="text.disabled" sx={{ fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Source Articles
                  </Typography>
                  <Box sx={{ mt: 0.5, display: "flex", flexDirection: "column", gap: 0.5 }}>
                    {result.article_links.map((a, i) => (
                      <Box key={i} sx={{ display: "flex", alignItems: "flex-start", gap: 0.75 }}>
                        <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.65rem", flexShrink: 0, mt: 0.1 }}>
                          {i + 1}.
                        </Typography>
                        <Box>
                          {a.url ? (
                            <Link href={a.url} target="_blank" rel="noopener noreferrer" underline="hover"
                              sx={{ fontSize: "0.75rem", color: "text.primary", display: "flex", alignItems: "center", gap: 0.5 }}>
                              {a.title || a.url}
                              <OpenInNewIcon sx={{ fontSize: 10 }} />
                            </Link>
                          ) : (
                            <Typography variant="caption" sx={{ fontSize: "0.75rem" }}>{a.title}</Typography>
                          )}
                          {a.date && (
                            <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.62rem", display: "block" }}>
                              {a.date}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          </Collapse>
        </>
      )}
    </Paper>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface Props {
  topicRunId: number;
}

export const TopicRunDetail = ({ topicRunId }: Props) => {
  const [baselineExpanded, setBaselineExpanded] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["topic-run", topicRunId],
    queryFn: () => fetchTopicRun(topicRunId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 8000 : false;
    },
    staleTime: 5000,
  });

  if (isLoading || !data) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh", gap: 2 }}>
        <CircularProgress size={28} />
        <Typography color="text.secondary">Loading topic analysis…</Typography>
      </Box>
    );
  }

  const isPending = data.status === "pending" || data.status === "running";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      {/* Page header */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
        <Box
          sx={{
            width: 36, height: 36, borderRadius: 2, flexShrink: 0,
            backgroundColor: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.2)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          <TravelExploreIcon sx={{ fontSize: 20, color: "#8b5cf6" }} />
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.2 }}>
            {data.topic}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.25, flexWrap: "wrap" }}>
            <Chip
              label={data.status.toUpperCase()}
              size="small"
              color={
                data.status === "completed" ? "success" :
                data.status === "failed" ? "error" :
                data.status === "running" ? "primary" : "default"
              }
              sx={data.status === "running" ? { animation: "pulse-glow 2s cubic-bezier(0.4,0,0.6,1) infinite" } : {}}
            />
            <Typography variant="caption" color="text.secondary">
              {data.outlets_found} outlet{data.outlets_found !== 1 ? "s" : ""} analysed
              · {new Date(data.created_at).toLocaleString()}
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Running indicator */}
      {isPending && (
        <Box sx={{
          display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.5,
          backgroundColor: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)",
          borderRadius: 2,
        }}>
          <CircularProgress size={16} />
          <Box>
            <Typography variant="body2" fontWeight={600}>
              {data.status === "pending" ? "Queued — waiting to start…" : "Running — fetching and analysing outlets…"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Results appear as each outlet is analysed. This page refreshes automatically.
            </Typography>
          </Box>
        </Box>
      )}

      {/* Error */}
      {data.status === "failed" && data.error && (
        <Box sx={{
          px: 2, py: 1.5, backgroundColor: "rgba(239,68,68,0.06)",
          border: "1px solid rgba(239,68,68,0.2)", borderRadius: 2,
        }}>
          <Typography variant="body2" color="error" fontWeight={600}>Analysis failed</Typography>
          <Typography variant="caption" color="text.secondary">{data.error}</Typography>
        </Box>
      )}

      {/* Baseline reference box */}
      {data.baseline_summary && (
        <Paper sx={{
          border: "1px solid rgba(16,185,129,0.2)", backgroundColor: "rgba(16,185,129,0.04)",
          borderRadius: 2, overflow: "hidden",
        }}>
          <Box
            sx={{
              display: "flex", alignItems: "center", px: 2, py: 1.25, gap: 1,
              cursor: "pointer", "&:hover": { backgroundColor: "rgba(16,185,129,0.04)" },
            }}
            onClick={() => setBaselineExpanded((e) => !e)}
          >
            <VerifiedIcon sx={{ fontSize: 16, color: "#10b981", flexShrink: 0 }} />
            <Typography variant="subtitle2" fontWeight={700} sx={{ flexGrow: 1 }}>
              Neutral Baseline Reference
            </Typography>
            <Chip
              label="Reuters · BBC · AP · AFP"
              size="small"
              sx={{ height: 16, fontSize: "0.6rem", backgroundColor: "rgba(16,185,129,0.1)", color: "#10b981", "& .MuiChip-label": { px: 0.75 } }}
            />
            <IconButton size="small" sx={{ p: 0.25, color: "#10b981" }}>
              {baselineExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          </Box>
          <Collapse in={baselineExpanded}>
            <Divider sx={{ borderColor: "rgba(16,185,129,0.15)" }} />
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="body2" sx={{ lineHeight: 1.65, color: "text.secondary", fontSize: "0.82rem" }}>
                {data.baseline_summary}
              </Typography>
            </Box>
          </Collapse>
        </Paper>
      )}

      {/* Coordination signal — shown once pipeline completes */}
      {data.status === "completed" && data.coordination_signal !== null && data.coordination_signal !== undefined && data.coordination_signal > 0 && (
        <CoordinationBanner
          signal={data.coordination_signal}
          detail={data.coordination_detail ?? null}
        />
      )}

      {/* Outlet results */}
      {data.outlet_results.length > 0 && (
        <Box>
          <Typography variant="overline" color="text.secondary" sx={{ fontSize: "0.65rem", mb: 1, display: "block" }}>
            Outlets ranked by narrative divergence from neutral baseline
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            {data.outlet_results.map((result) => (
              <OutletCard key={result.id} result={result} />
            ))}
          </Box>
        </Box>
      )}

      {/* Empty state while running */}
      {isPending && data.outlet_results.length === 0 && (
        <Box sx={{ textAlign: "center", py: 6 }}>
          <TravelExploreIcon sx={{ fontSize: 48, color: "text.disabled", mb: 1.5 }} />
          <Typography color="text.secondary">Discovering outlets covering this topic…</Typography>
        </Box>
      )}
    </Box>
  );
};
