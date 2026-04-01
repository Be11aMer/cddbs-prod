import {
  Box,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  LinearProgress,
  Stack,
  Alert,
  CircularProgress,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import ShieldIcon from "@mui/icons-material/Shield";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchSourceCredibility,
  refreshSourceCredibility,
  type SourceCredibilityItem,
} from "../api";

function getReliabilityColor(index: number): string {
  if (index >= 0.7) return "#10b981"; // green — reliable
  if (index >= 0.4) return "#f59e0b"; // amber — caution
  return "#ef4444";                   // red — adversarial
}

function TrendIcon({ direction }: { direction: string }) {
  if (direction === "improving")
    return <TrendingUpIcon sx={{ fontSize: 14, color: "#10b981" }} />;
  if (direction === "degrading")
    return <TrendingDownIcon sx={{ fontSize: 14, color: "#ef4444" }} />;
  return <TrendingFlatIcon sx={{ fontSize: 14, color: "#94a3b8" }} />;
}

function CredibilityBar({ value }: { value: number }) {
  const color = getReliabilityColor(value);
  return (
    <LinearProgress
      variant="determinate"
      value={value * 100}
      sx={{
        height: 4,
        borderRadius: 2,
        backgroundColor: "rgba(148,163,184,0.1)",
        "& .MuiLinearProgress-bar": { backgroundColor: color, borderRadius: 2 },
      }}
    />
  );
}

function SourceRow({ item }: { item: SourceCredibilityItem }) {
  const color = getReliabilityColor(item.reliability_index);
  const isHighRisk = item.reliability_index < 0.4;

  return (
    <Box
      sx={{
        py: 1,
        px: 1.5,
        borderBottom: "1px solid rgba(148,163,184,0.07)",
        "&:last-child": { borderBottom: "none" },
        backgroundColor: isHighRisk ? "rgba(239,68,68,0.03)" : "transparent",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
        {isHighRisk && (
          <WarningAmberIcon sx={{ fontSize: 12, color: "#ef4444", flexShrink: 0 }} />
        )}
        <Typography
          variant="caption"
          fontWeight={700}
          sx={{ color: "text.primary", fontSize: "0.78rem", flexGrow: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
        >
          {item.source_domain}
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexShrink: 0 }}>
          <TrendIcon direction={item.trend_direction} />
          <Typography variant="caption" fontWeight={700} sx={{ color, fontSize: "0.72rem" }}>
            {(item.reliability_index * 100).toFixed(0)}%
          </Typography>
        </Box>
      </Box>

      <CredibilityBar value={item.reliability_index} />

      <Box sx={{ display: "flex", gap: 1.5, mt: 0.5, flexWrap: "wrap" }}>
        <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.62rem" }}>
          {item.total_articles} articles
        </Typography>
        {item.avg_propaganda_score > 0 && (
          <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.62rem" }}>
            prop. {(item.avg_propaganda_score * 100).toFixed(0)}%
          </Typography>
        )}
        {item.coordination_count > 0 && (
          <Tooltip title="Times flagged in coordination indicators">
            <Typography variant="caption" sx={{ color: "#f59e0b", fontSize: "0.62rem" }}>
              ⚡ {item.coordination_count}x coord
            </Typography>
          </Tooltip>
        )}
        {item.burst_participation_count > 0 && (
          <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.62rem" }}>
            {item.burst_participation_count}x burst
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export function SourceCredibilityPanel() {
  const queryClient = useQueryClient();
  const [trendFilter, setTrendFilter] = useState<string>("");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["source-credibility", trendFilter],
    queryFn: () => fetchSourceCredibility({
      min_articles: 5,
      trend_direction: trendFilter || undefined,
      limit: 100,
    }),
    refetchInterval: 120_000,
  });

  const refreshMutation = useMutation({
    mutationFn: refreshSourceCredibility,
    onSuccess: () => {
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["source-credibility"] }), 3000);
    },
  });

  const items = data ?? [];
  const adversarial = items.filter((i) => i.reliability_index < 0.4);
  const caution = items.filter((i) => i.reliability_index >= 0.4 && i.reliability_index < 0.7);
  const reliable = items.filter((i) => i.reliability_index >= 0.7);

  return (
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
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 1.5,
          borderBottom: "1px solid rgba(148,163,184,0.08)",
          flexShrink: 0,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <ShieldIcon sx={{ fontSize: 16, color: "#10b981" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Source Credibility
          </Typography>
          {items.length > 0 && (
            <Chip
              label={items.length}
              size="small"
              sx={{ height: 16, fontSize: "0.6rem", fontWeight: 700, backgroundColor: "rgba(16,185,129,0.1)", color: "#10b981", "& .MuiChip-label": { px: 0.75 } }}
            />
          )}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <FormControl size="small" sx={{ minWidth: 110 }}>
            <InputLabel sx={{ fontSize: "0.7rem" }}>Trend</InputLabel>
            <Select
              value={trendFilter}
              label="Trend"
              onChange={(e) => setTrendFilter(e.target.value)}
              sx={{ fontSize: "0.7rem" }}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="degrading">Degrading</MenuItem>
              <MenuItem value="stable">Stable</MenuItem>
              <MenuItem value="improving">Improving</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title="Refresh scores">
            <span>
              <IconButton
                size="small"
                onClick={() => refetch()}
                sx={{ color: "text.secondary" }}
              >
                <RefreshIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Recompute credibility scores now">
            <span>
              <IconButton
                size="small"
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                sx={{ color: refreshMutation.isPending ? "text.disabled" : "#10b981" }}
              >
                {refreshMutation.isPending
                  ? <CircularProgress size={14} />
                  : <ShieldIcon sx={{ fontSize: 16 }} />
                }
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      </Box>

      {/* Summary stats */}
      {!isLoading && items.length > 0 && (
        <Box sx={{ display: "flex", px: 2, py: 1, gap: 2, borderBottom: "1px solid rgba(148,163,184,0.06)", flexShrink: 0 }}>
          <Box sx={{ textAlign: "center" }}>
            <Typography variant="caption" sx={{ color: "#ef4444", fontWeight: 700, fontSize: "0.85rem" }}>{adversarial.length}</Typography>
            <Typography variant="caption" sx={{ color: "text.disabled", display: "block", fontSize: "0.6rem" }}>Adversarial</Typography>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Typography variant="caption" sx={{ color: "#f59e0b", fontWeight: 700, fontSize: "0.85rem" }}>{caution.length}</Typography>
            <Typography variant="caption" sx={{ color: "text.disabled", display: "block", fontSize: "0.6rem" }}>Caution</Typography>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Typography variant="caption" sx={{ color: "#10b981", fontWeight: 700, fontSize: "0.85rem" }}>{reliable.length}</Typography>
            <Typography variant="caption" sx={{ color: "text.disabled", display: "block", fontSize: "0.6rem" }}>Reliable</Typography>
          </Box>
        </Box>
      )}

      {/* List */}
      <Box sx={{ flexGrow: 1, overflowY: "auto", "&::-webkit-scrollbar": { width: 4 }, "&::-webkit-scrollbar-thumb": { backgroundColor: "rgba(148,163,184,0.2)", borderRadius: 2 } }}>
        {isLoading && (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", gap: 1.5 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">Computing scores…</Typography>
          </Box>
        )}

        {!isLoading && items.length === 0 && (
          <Box sx={{ p: 2.5 }}>
            <Alert severity="info" sx={{ backgroundColor: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)", fontSize: "0.78rem" }}>
              No credibility data yet. Scores are computed once domains have ≥5 articles and SitReps with framing analysis have been generated.
            </Alert>
          </Box>
        )}

        {!isLoading && items.length > 0 && (
          <Stack>
            {items.map((item) => (
              <SourceRow key={item.id} item={item} />
            ))}
          </Stack>
        )}
      </Box>

      {/* Legend */}
      {items.length > 0 && (
        <Box sx={{ px: 2, py: 1, borderTop: "1px solid rgba(148,163,184,0.06)", display: "flex", gap: 2, flexShrink: 0 }}>
          {[
            { color: "#10b981", label: "≥70% reliable" },
            { color: "#f59e0b", label: "40–69% caution" },
            { color: "#ef4444", label: "<40% adversarial" },
          ].map(({ color, label }) => (
            <Box key={label} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Box sx={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: color }} />
              <Typography variant="caption" sx={{ color: "text.disabled", fontSize: "0.6rem" }}>{label}</Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
