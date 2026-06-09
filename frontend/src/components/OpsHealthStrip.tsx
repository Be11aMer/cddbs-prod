import { Box, Typography, Stack, Tooltip, Skeleton } from "@mui/material";
import BubbleChartIcon from "@mui/icons-material/BubbleChart";
import FlagIcon from "@mui/icons-material/Flag";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import StorageIcon from "@mui/icons-material/Storage";
import type { ReactNode } from "react";
import type { GlobalStats } from "../api";
import { SEVERITY_COLORS } from "../utils/severity";

interface StatProps {
  icon: ReactNode;
  label: string;
  value: number;
  color: string;
  tooltip: string;
}

const Stat = ({ icon, label, value, color, tooltip }: StatProps) => (
  <Tooltip title={tooltip}>
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.85 }}>
      <Box sx={{ display: "flex", color, fontSize: 16 }}>{icon}</Box>
      <Typography variant="body2" fontWeight={800} sx={{ color, lineHeight: 1, fontSize: "0.95rem" }}>
        {value}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.7rem", whiteSpace: "nowrap" }}>
        {label}
      </Typography>
    </Box>
  </Tooltip>
);

const Sep = () => (
  <Box sx={{ width: "1px", height: 22, backgroundColor: "rgba(148,163,184,0.15)", display: { xs: "none", sm: "block" } }} />
);

interface Props {
  stats?: GlobalStats;
  isLoading: boolean;
  /** Count of currently-active events whose narrative_risk_score crosses the exploitation threshold */
  exploitedCount: number;
}

/**
 * Thin operational status row — replaces the old six-card vanity-metric grid.
 * Surfaces only what an analyst needs to know "is the pipeline running and is
 * anything happening that needs attention right now," not cumulative totals.
 */
export const OpsHealthStrip = ({ stats, isLoading, exploitedCount }: Props) => {
  if (isLoading || !stats) {
    return <Skeleton variant="rounded" height={44} sx={{ borderRadius: 2.5, backgroundColor: "rgba(255,255,255,0.04)" }} />;
  }

  const activeEvents = stats.active_events ?? 0;
  const activeBursts = stats.active_bursts ?? 0;

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: { xs: 1.5, sm: 2.5 },
        flexWrap: "wrap",
        px: 2,
        py: 1.25,
        borderRadius: 2.5,
        backgroundColor: "rgba(12, 20, 56, 0.6)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(148,163,184,0.1)",
      }}
    >
      <Stack direction="row" spacing={2.5} alignItems="center" sx={{ flexWrap: "wrap", gap: 1.5 }}>
        <Stat
          icon={<BubbleChartIcon sx={{ fontSize: 16 }} />}
          label="events being watched"
          value={activeEvents}
          color={activeEvents > 0 ? SEVERITY_COLORS.info : SEVERITY_COLORS.neutral}
          tooltip="Real-world event clusters currently active in the monitoring pipeline"
        />
        <Sep />
        <Stat
          icon={<FlagIcon sx={{ fontSize: 16 }} />}
          label="exploitation flags"
          value={exploitedCount}
          color={exploitedCount > 0 ? SEVERITY_COLORS.critical : SEVERITY_COLORS.good}
          tooltip="Currently-active events whose narrative-risk score indicates disinformation is exploiting them"
        />
        <Sep />
        <Stat
          icon={<TrendingUpIcon sx={{ fontSize: 16 }} />}
          label="active narrative bursts"
          value={activeBursts}
          color={activeBursts > 0 ? SEVERITY_COLORS.warning : SEVERITY_COLORS.good}
          tooltip="Keyword/topic frequency spikes (z-score ≥ 3) detected in the last monitoring window"
        />
      </Stack>

      <Box sx={{ ml: "auto", display: "flex", alignItems: "center", gap: 0.6, opacity: 0.55 }}>
        <StorageIcon sx={{ fontSize: 13, color: "text.disabled" }} />
        <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.68rem" }}>
          {stats.articles_ingested.toLocaleString()} articles ingested · {stats.countries_monitored} countries · {stats.total_analyses} analyses to date
        </Typography>
      </Box>
    </Box>
  );
};
