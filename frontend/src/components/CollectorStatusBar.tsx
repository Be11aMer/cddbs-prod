import { Box, Typography, Chip, Tooltip } from "@mui/material";
import SyncIcon from "@mui/icons-material/Sync";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import { useQuery } from "@tanstack/react-query";
import { fetchCollectorStatus, type CollectorStatusItem } from "../api";

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "never";
  try {
    const diffMs = Date.now() - new Date(dateStr).getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    return `${Math.floor(diffMins / 60)}h ago`;
  } catch {
    return "unknown";
  }
}

function CollectorChip({ collector }: { collector: CollectorStatusItem }) {
  const hasError = !!collector.last_error;
  const isRunning = collector.is_running;

  const tooltipText = [
    `Last run: ${formatTimeAgo(collector.last_run)}`,
    `Articles last batch: ${collector.last_article_count}`,
    `Total collected: ${collector.total_articles_collected}`,
    hasError ? `Error: ${collector.last_error}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <Tooltip title={<span style={{ whiteSpace: "pre-line" }}>{tooltipText}</span>} arrow>
      <Chip
        icon={
          isRunning ? (
            <SyncIcon sx={{ fontSize: 10, animation: "spin 1s linear infinite" }} />
          ) : hasError ? (
            <ErrorIcon sx={{ fontSize: 10 }} />
          ) : (
            <CheckCircleIcon sx={{ fontSize: 10 }} />
          )
        }
        label={`${collector.name.toUpperCase()} · ${collector.total_articles_collected}`}
        size="small"
        sx={{
          height: 18,
          fontSize: "0.55rem",
          fontWeight: 700,
          letterSpacing: "0.03em",
          backgroundColor: hasError
            ? "rgba(239,68,68,0.1)"
            : isRunning
              ? "rgba(59,130,246,0.1)"
              : "rgba(16,185,129,0.08)",
          color: hasError ? "#ef4444" : isRunning ? "#3b82f6" : "#10b981",
          border: `1px solid ${hasError ? "rgba(239,68,68,0.2)" : isRunning ? "rgba(59,130,246,0.2)" : "rgba(16,185,129,0.2)"}`,
          "& .MuiChip-label": { px: 0.75 },
          "& .MuiChip-icon": { ml: 0.5, mr: -0.25 },
          "@keyframes spin": {
            "0%": { transform: "rotate(0deg)" },
            "100%": { transform: "rotate(360deg)" },
          },
        }}
      />
    </Tooltip>
  );
}

export const CollectorStatusBar = () => {
  const { data: collectors } = useQuery({
    queryKey: ["collector-status"],
    queryFn: fetchCollectorStatus,
    refetchInterval: 30 * 1000,
    staleTime: 15 * 1000,
  });

  if (!collectors || collectors.length === 0) return null;

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flexWrap: "wrap" }}>
      <Typography
        variant="caption"
        color="text.disabled"
        sx={{ fontSize: "0.6rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}
      >
        Collectors:
      </Typography>
      {collectors.map((c) => (
        <CollectorChip key={c.name} collector={c} />
      ))}
    </Box>
  );
};
