import { Box, Typography, Chip, CircularProgress, Stack, Tooltip } from "@mui/material";
import ShieldIcon from "@mui/icons-material/Shield";
import VisibilityIcon from "@mui/icons-material/Visibility";
import GavelIcon from "@mui/icons-material/Gavel";
import NotesIcon from "@mui/icons-material/Notes";
import { useQuery, useQueries } from "@tanstack/react-query";
import { useState } from "react";
import { fetchLatestThreatBriefings, fetchThreatBriefing, type ThreatBriefingItem } from "../api";
import { ThreatBriefingDetail } from "./ThreatBriefingDetail";
import { SectionHeader } from "./SectionHeader";
import { SEVERITY_COLORS } from "../utils/severity";

const RISK_COLORS: Record<string, string> = {
  critical: SEVERITY_COLORS.critical,
  high: "#f97316",
  moderate: SEVERITY_COLORS.warning,
  low: SEVERITY_COLORS.good,
};

type ResponseKind = "recommended_action" | "recommendation" | "analyst_guidance" | "outlook";

const KIND_META: Record<ResponseKind, { label: string; icon: JSX.Element; color: string }> = {
  recommended_action: { label: "Recommended response", icon: <GavelIcon sx={{ fontSize: 13 }} />, color: SEVERITY_COLORS.good },
  recommendation: { label: "Strategic recommendation", icon: <ShieldIcon sx={{ fontSize: 13 }} />, color: SEVERITY_COLORS.info },
  analyst_guidance: { label: "Analyst guidance", icon: <NotesIcon sx={{ fontSize: 13 }} />, color: SEVERITY_COLORS.accent },
  outlook: { label: "What to watch for", icon: <VisibilityIcon sx={{ fontSize: 13 }} />, color: SEVERITY_COLORS.neutral },
};

interface ResponseItem {
  kind: ResponseKind;
  text: string;
  urgency: string | null; // risk_level when available, used for severity coloring
  briefingId: number;
  briefingTitle: string;
  createdAt: string | null;
}

function extractResponseItems(briefing: ThreatBriefingItem & { briefing_json: Record<string, unknown> | null }): ResponseItem[] {
  const bjson = briefing.briefing_json;
  if (!bjson) return [];
  const items: ResponseItem[] = [];
  const base = { briefingId: briefing.id, briefingTitle: briefing.title || "Untitled briefing", createdAt: briefing.created_at };

  const topThreats = (bjson.top_threats as Record<string, string>[]) ?? [];
  for (const t of topThreats) {
    if (t.recommended_action) {
      items.push({ kind: "recommended_action", text: `${t.event ? `${t.event}: ` : ""}${t.recommended_action}`, urgency: t.risk_level ?? null, ...base });
    }
  }

  const recommendations = (bjson.recommendations as string[]) ?? [];
  for (const r of recommendations) {
    items.push({ kind: "recommendation", text: r, urgency: null, ...base });
  }

  if (typeof bjson.analyst_notes === "string" && bjson.analyst_notes.trim()) {
    items.push({ kind: "analyst_guidance", text: bjson.analyst_notes, urgency: null, ...base });
  }

  if (typeof bjson.outlook === "string" && bjson.outlook.trim()) {
    items.push({ kind: "outlook", text: bjson.outlook, urgency: null, ...base });
  }

  return items;
}

function ResponseRow({ item, onOpenBriefing }: { item: ResponseItem; onOpenBriefing: (id: number) => void }) {
  const meta = KIND_META[item.kind];
  const urgencyColor = item.urgency ? (RISK_COLORS[item.urgency.toLowerCase()] ?? SEVERITY_COLORS.neutral) : meta.color;

  return (
    <Box
      sx={{
        p: 1.25,
        borderRadius: 1.5,
        border: "1px solid rgba(148,163,184,0.1)",
        backgroundColor: "rgba(255,255,255,0.02)",
        borderLeft: `3px solid ${urgencyColor}`,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5, flexWrap: "wrap" }}>
        <Chip
          size="small"
          icon={meta.icon}
          label={meta.label}
          sx={{
            height: 18,
            fontSize: "0.6rem",
            fontWeight: 700,
            backgroundColor: `${meta.color}1a`,
            color: meta.color,
            "& .MuiChip-icon": { color: meta.color, ml: 0.5 },
          }}
        />
        {item.urgency && (
          <Chip
            size="small"
            label={item.urgency.toUpperCase()}
            sx={{ height: 18, fontSize: "0.55rem", fontWeight: 800, backgroundColor: `${urgencyColor}1a`, color: urgencyColor }}
          />
        )}
        <Tooltip title="Open the source intelligence product">
          <Typography
            variant="caption"
            onClick={() => onOpenBriefing(item.briefingId)}
            sx={{ ml: "auto", color: "text.disabled", cursor: "pointer", fontSize: "0.65rem", "&:hover": { color: "primary.main" } }}
          >
            from “{item.briefingTitle}” →
          </Typography>
        </Tooltip>
      </Box>
      <Typography variant="body2" sx={{ color: "text.primary", fontSize: "0.8rem", lineHeight: 1.5 }}>
        {item.text}
      </Typography>
    </Box>
  );
}

/**
 * Surfaces "what should we do about this" guidance that already flows through
 * the threat-briefing pipeline today — recommended_action (digests),
 * recommendations[] (quarterly reports, previously not rendered anywhere),
 * analyst_notes (sitreps), and outlook — under one consolidated, clearly
 * labeled "Countermeasures" lens. This is a relabeling/aggregation of existing
 * AI-generated analyst guidance, not a novel recommendation engine; a future
 * structured countermeasures schema (type/urgency/confidence, new Gemini
 * prompt work) would be a deliberate next step on top of this.
 */
export const CountermeasuresPanel = () => {
  const [openBriefingId, setOpenBriefingId] = useState<number | null>(null);

  const { data: briefings, isLoading: listLoading } = useQuery({
    queryKey: ["threat-briefings-latest", "countermeasures"],
    queryFn: () => fetchLatestThreatBriefings(8),
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });

  const detailQueries = useQueries({
    queries: (briefings ?? []).map((b) => ({
      queryKey: ["threat-briefing", b.id],
      queryFn: () => fetchThreatBriefing(b.id),
      staleTime: 60 * 1000,
    })),
  });

  const isLoading = listLoading || detailQueries.some((q) => q.isLoading);

  const items = detailQueries
    .map((q) => q.data)
    .filter((d): d is NonNullable<typeof d> => d != null)
    .flatMap(extractResponseItems)
    .sort((a, b) => {
      const order: Record<ResponseKind, number> = { recommended_action: 0, recommendation: 1, analyst_guidance: 2, outlook: 3 };
      return order[a.kind] - order[b.kind];
    });

  return (
    <>
      <Box
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "rgba(12, 20, 56, 0.6)",
          backdropFilter: "blur(10px)",
          border: "1px solid rgba(148,163,184,0.1)",
          borderRadius: 3,
          overflow: "hidden",
          p: 2,
          gap: 1.5,
        }}
      >
        <SectionHeader
          icon={<ShieldIcon sx={{ fontSize: 20 }} />}
          title="Countermeasures"
          subtitle="Recommended response &amp; analyst guidance, synthesized from the latest intelligence products"
          accentColor={SEVERITY_COLORS.good}
          badge={items.length > 0 ? items.length : undefined}
        />

        <Box
          sx={{
            flexGrow: 1,
            overflowY: "auto",
            "&::-webkit-scrollbar": { width: 4 },
            "&::-webkit-scrollbar-thumb": { backgroundColor: "rgba(148,163,184,0.2)", borderRadius: 2 },
          }}
        >
          {isLoading && (
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", gap: 1.5 }}>
              <CircularProgress size={20} />
              <Typography variant="body2" color="text.secondary">Synthesizing response guidance...</Typography>
            </Box>
          )}

          {!isLoading && items.length === 0 && (
            <Box sx={{ p: 3, textAlign: "center" }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                No response guidance available yet
              </Typography>
              <Typography variant="caption" color="text.disabled">
                Countermeasure suggestions are derived from generated SitReps, digests, and quarterly reports
              </Typography>
            </Box>
          )}

          {!isLoading && items.length > 0 && (
            <Stack spacing={1}>
              {items.map((item, i) => (
                <ResponseRow key={`${item.briefingId}-${item.kind}-${i}`} item={item} onOpenBriefing={setOpenBriefingId} />
              ))}
            </Stack>
          )}
        </Box>
      </Box>

      <ThreatBriefingDetail
        briefingId={openBriefingId}
        open={openBriefingId !== null}
        onClose={() => setOpenBriefingId(null)}
      />
    </>
  );
};
