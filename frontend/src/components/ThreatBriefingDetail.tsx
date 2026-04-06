import {
  Box,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  Grid,
  Tooltip,
  Stack,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import GroupsIcon from "@mui/icons-material/Groups";
import { useQuery } from "@tanstack/react-query";
import { fetchThreatBriefing, type FramingAnalysis } from "../api";

const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  moderate: "#f59e0b",
  low: "#10b981",
  unknown: "#94a3b8",
};

const TYPE_LABELS: Record<string, string> = {
  sitrep: "SitRep",
  daily_digest: "Daily Digest",
  quarterly_report: "Quarterly Report",
};

function RiskChip({ level }: { level: string }) {
  const color = RISK_COLORS[level?.toLowerCase()] || RISK_COLORS.unknown;
  return (
    <Chip
      size="small"
      label={level?.toUpperCase() || "UNKNOWN"}
      sx={{ backgroundColor: `${color}22`, color, borderColor: `${color}44`, border: "1px solid", fontWeight: 700, fontSize: "0.65rem" }}
    />
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="overline" sx={{ color: "text.secondary", fontWeight: 800, fontSize: "0.65rem", letterSpacing: "0.1em", display: "block", mt: 3, mb: 1 }}>
      {children}
    </Typography>
  );
}

function FramingSection({ framing }: { framing: FramingAnalysis }) {
  const divergenceColor = framing.framing_divergence_score >= 0.7 ? "#ef4444"
    : framing.framing_divergence_score >= 0.4 ? "#f59e0b" : "#10b981";

  return (
    <Box>
      <Divider sx={{ my: 2, opacity: 0.1 }} />
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
        <CompareArrowsIcon sx={{ fontSize: 18, color: "primary.main" }} />
        <Typography variant="subtitle2" fontWeight={700} sx={{ color: "primary.main" }}>
          Cross-Source Framing Analysis
        </Typography>
        <Tooltip title="Divergence score: how differently sources frame this event (0 = aligned, 1 = contradictory)">
          <Chip
            size="small"
            label={`Divergence: ${(framing.framing_divergence_score * 100).toFixed(0)}%`}
            sx={{ ml: "auto", backgroundColor: `${divergenceColor}22`, color: divergenceColor, fontWeight: 700, fontSize: "0.65rem" }}
          />
        </Tooltip>
      </Box>

      {/* Per-source framings */}
      {framing.source_framings?.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <SectionHeader>Source Framings</SectionHeader>
          <Grid container spacing={1.5}>
            {framing.source_framings.map((sf, i) => (
              <Grid item xs={12} sm={6} key={i}>
                <Box sx={{ p: 1.5, borderRadius: 1.5, border: "1px solid rgba(148,163,184,0.12)", backgroundColor: "rgba(255,255,255,0.02)" }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.75 }}>
                    <Typography variant="caption" fontWeight={700} sx={{ color: "primary.light" }}>{sf.source_domain}</Typography>
                    <Chip size="small" label={sf.source_type} sx={{ fontSize: "0.6rem", height: 16 }} />
                    {sf.bias_direction && sf.bias_direction !== "neutral" && (
                      <Chip size="small" label={sf.bias_direction} sx={{ fontSize: "0.6rem", height: 16, color: "#f59e0b", backgroundColor: "#f59e0b22" }} />
                    )}
                    <Tooltip title={`Emotional language score: ${(sf.emotional_language_score * 100).toFixed(0)}%`}>
                      <Box sx={{ ml: "auto", fontSize: "0.65rem", color: sf.emotional_language_score > 0.5 ? "#ef4444" : "text.secondary" }}>
                        🔥 {(sf.emotional_language_score * 100).toFixed(0)}%
                      </Box>
                    </Tooltip>
                  </Box>
                  <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 0.5 }}>{sf.framing_summary}</Typography>
                  {sf.omitted_facts?.length > 0 && (
                    <Box sx={{ mt: 0.5 }}>
                      <Typography variant="caption" sx={{ color: "#f59e0b", fontWeight: 700 }}>Omissions: </Typography>
                      <Typography variant="caption" sx={{ color: "text.secondary" }}>{sf.omitted_facts.join(" · ")}</Typography>
                    </Box>
                  )}
                </Box>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Discrepancies */}
      {framing.discrepancies?.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <SectionHeader>Discrepancies</SectionHeader>
          <Stack spacing={0.75}>
            {framing.discrepancies.map((d, i) => (
              <Box key={i} sx={{ p: 1.25, borderRadius: 1, border: "1px solid rgba(239,68,68,0.15)", backgroundColor: "rgba(239,68,68,0.04)" }}>
                <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
                  <WarningAmberIcon sx={{ fontSize: 14, color: "#f59e0b", mt: 0.25, flexShrink: 0 }} />
                  <Box>
                    <Typography variant="caption" fontWeight={700} sx={{ color: "text.primary", display: "block" }}>{d.topic}</Typography>
                    <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>{d.source_a}</Typography>
                    <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>{d.source_b}</Typography>
                    <Chip size="small" label={d.assessment} sx={{ mt: 0.5, fontSize: "0.6rem", height: 16, color: "#f59e0b", backgroundColor: "#f59e0b22" }} />
                  </Box>
                </Box>
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      {/* Coordination indicators */}
      {framing.coordination_indicators?.length > 0 && (
        <Box>
          <SectionHeader>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <GroupsIcon sx={{ fontSize: 14 }} />
              Coordination Indicators
            </Box>
          </SectionHeader>
          <Stack spacing={0.5}>
            {framing.coordination_indicators.map((ci, i) => (
              <Box key={i} sx={{ display: "flex", gap: 1 }}>
                <Box sx={{ width: 4, height: 4, borderRadius: "50%", backgroundColor: "#ef4444", mt: 0.75, flexShrink: 0 }} />
                <Typography variant="caption" sx={{ color: "text.secondary" }}>{ci}</Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      )}
    </Box>
  );
}

interface Props {
  briefingId: number | null;
  open: boolean;
  onClose: () => void;
}

export function ThreatBriefingDetail({ briefingId, open, onClose }: Props) {
  const { data: briefing, isLoading, error } = useQuery({
    queryKey: ["threat-briefing", briefingId],
    queryFn: () => fetchThreatBriefing(briefingId!),
    enabled: open && briefingId !== null,
  });

  const bjson = briefing?.briefing_json as Record<string, unknown> | null | undefined;
  const disinfo = bjson?.disinformation_risk as Record<string, unknown> | undefined;
  const eventAssessment = bjson?.event_assessment as Record<string, unknown> | undefined;
  const topThreats = (bjson?.top_threats as unknown[]) ?? [];
  const riskLevel = (disinfo?.risk_level as string) || "unknown";
  const typeLabel = TYPE_LABELS[briefing?.briefing_type ?? ""] || briefing?.briefing_type;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper"
      PaperProps={{ sx: { backgroundColor: "#0f172a", backgroundImage: "none", border: "1px solid rgba(148,163,184,0.1)" } }}
    >
      <DialogTitle sx={{ display: "flex", alignItems: "flex-start", gap: 1, pb: 1 }}>
        <Box sx={{ flexGrow: 1 }}>
          {briefing && (
            <Box sx={{ display: "flex", gap: 1, mb: 0.5, flexWrap: "wrap" }}>
              <Chip size="small" label={typeLabel} sx={{ fontSize: "0.65rem", fontWeight: 700, backgroundColor: "rgba(59,130,246,0.15)", color: "#3b82f6" }} />
              {riskLevel !== "unknown" && <RiskChip level={riskLevel} />}
              {briefing.has_framing_analysis && (
                <Chip size="small" icon={<CompareArrowsIcon sx={{ fontSize: 12 }} />} label="Framing Analysis" sx={{ fontSize: "0.65rem", backgroundColor: "rgba(139,92,246,0.15)", color: "#8b5cf6" }} />
              )}
            </Box>
          )}
          <Typography variant="h6" fontWeight={700} sx={{ fontSize: "1rem", lineHeight: 1.3 }}>
            {isLoading ? "Loading…" : (briefing?.title || "Threat Briefing")}
          </Typography>
          {briefing?.created_at && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {new Date(briefing.created_at).toLocaleString()} · {briefing.articles_analyzed} articles · {briefing.sources_compared} sources
            </Typography>
          )}
        </Box>
        <IconButton size="small" onClick={onClose} sx={{ color: "text.secondary", mt: 0.5 }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ borderColor: "rgba(148,163,184,0.1)" }}>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress size={32} />
          </Box>
        )}
        {error && <Alert severity="error">Failed to load briefing details.</Alert>}

        {briefing && bjson != null && (
          <Box>
            {/* Executive Summary */}
            {briefing.executive_summary && (
              <Box sx={{ p: 2, borderRadius: 1.5, backgroundColor: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)", mb: 2 }}>
                <Typography variant="body2" sx={{ color: "text.primary", lineHeight: 1.7 }}>
                  {briefing.executive_summary}
                </Typography>
              </Box>
            )}

            {/* SitRep-specific sections */}
            {briefing.briefing_type === "sitrep" && eventAssessment && (
              <>
                <SectionHeader>Event Assessment</SectionHeader>
                <Grid container spacing={2} sx={{ mb: 1 }}>
                  {!!eventAssessment.what_happened && (
                    <Grid item xs={12}>
                      <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>
                        {String(eventAssessment.what_happened)}
                      </Typography>
                    </Grid>
                  )}
                  {((eventAssessment.key_actors as string[]) ?? []).length > 0 && (
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" fontWeight={700} sx={{ color: "text.primary", display: "block", mb: 0.5 }}>Key Actors</Typography>
                      {(eventAssessment.key_actors as string[]).map((a, i) => (
                        <Chip key={i} size="small" label={a} sx={{ mr: 0.5, mb: 0.5, fontSize: "0.65rem" }} />
                      ))}
                    </Grid>
                  )}
                  {((eventAssessment.affected_regions as string[]) ?? []).length > 0 && (
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" fontWeight={700} sx={{ color: "text.primary", display: "block", mb: 0.5 }}>Affected Regions</Typography>
                      {(eventAssessment.affected_regions as string[]).map((r, i) => (
                        <Chip key={i} size="small" label={r} sx={{ mr: 0.5, mb: 0.5, fontSize: "0.65rem" }} />
                      ))}
                    </Grid>
                  )}
                </Grid>
              </>
            )}

            {/* Disinformation risk */}
            {disinfo && (
              <>
                <SectionHeader>Disinformation Risk</SectionHeader>
                <Grid container spacing={1.5} sx={{ mb: 1 }}>
                  {(disinfo.risk_factors as string[])?.length > 0 && (
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" fontWeight={700} sx={{ color: "text.primary", display: "block", mb: 0.5 }}>Risk Factors</Typography>
                      <Stack spacing={0.5}>
                        {(disinfo.risk_factors as string[]).map((f, i) => (
                          <Box key={i} sx={{ display: "flex", gap: 1 }}>
                            <Box sx={{ width: 4, height: 4, borderRadius: "50%", backgroundColor: "#ef4444", mt: 0.75, flexShrink: 0 }} />
                            <Typography variant="caption" sx={{ color: "text.secondary" }}>{f}</Typography>
                          </Box>
                        ))}
                      </Stack>
                    </Grid>
                  )}
                  {(disinfo.unverified_claims as string[])?.length > 0 && (
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" fontWeight={700} sx={{ color: "#f59e0b", display: "block", mb: 0.5 }}>Unverified Claims</Typography>
                      <Stack spacing={0.5}>
                        {(disinfo.unverified_claims as string[]).map((c, i) => (
                          <Typography key={i} variant="caption" sx={{ color: "text.secondary" }}>• {c}</Typography>
                        ))}
                      </Stack>
                    </Grid>
                  )}
                </Grid>
                {!!disinfo.narrative_alignment && (
                  <Typography variant="caption" sx={{ color: "text.secondary", fontStyle: "italic" }}>
                    Narrative alignment: {String(disinfo.narrative_alignment)}
                  </Typography>
                )}
              </>
            )}

            {/* Digest top threats */}
            {briefing.briefing_type === "daily_digest" && topThreats.length > 0 && (
              <>
                <SectionHeader>Top Threats</SectionHeader>
                <Stack spacing={1} sx={{ mb: 1 }}>
                  {topThreats.map((t: unknown, i: number) => {
                    const threat = t as Record<string, string>;
                    return (
                      <Box key={i} sx={{ p: 1.25, borderRadius: 1, border: "1px solid rgba(148,163,184,0.1)", backgroundColor: "rgba(255,255,255,0.02)" }}>
                        <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 0.5 }}>
                          <Typography variant="caption" fontWeight={700}>{threat.event}</Typography>
                          {threat.risk_level && <RiskChip level={threat.risk_level} />}
                        </Box>
                        {threat.key_concern && <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>{threat.key_concern}</Typography>}
                        {threat.recommended_action && (
                          <Typography variant="caption" sx={{ color: "#10b981", display: "block", mt: 0.5 }}>→ {threat.recommended_action}</Typography>
                        )}
                      </Box>
                    );
                  })}
                </Stack>
              </>
            )}

            {/* Outlook */}
            {!!bjson?.outlook && (
              <>
                <Divider sx={{ my: 2, opacity: 0.1 }} />
                <SectionHeader>Outlook</SectionHeader>
                <Typography variant="caption" sx={{ color: "text.secondary" }}>{String(bjson.outlook)}</Typography>
              </>
            )}

            {/* Analyst notes */}
            {!!bjson?.analyst_notes && (
              <>
                <Divider sx={{ my: 2, opacity: 0.1 }} />
                <SectionHeader>Analyst Notes</SectionHeader>
                <Typography variant="caption" sx={{ color: "text.secondary", fontStyle: "italic" }}>{String(bjson.analyst_notes)}</Typography>
              </>
            )}

            {/* Framing analysis */}
            {briefing.framing_analysis && (
              <FramingSection framing={briefing.framing_analysis} />
            )}
          </Box>
        )}

        {/* Placeholder state (generating...) */}
        {briefing && !bjson && !isLoading && (
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", py: 4, gap: 2 }}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              Report is being generated — refresh in a moment.
            </Typography>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}
