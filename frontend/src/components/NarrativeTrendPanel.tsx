import { Box, Typography, Chip, LinearProgress, Skeleton } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { useQuery } from "@tanstack/react-query";
import { fetchNarrativeTrends, type NarrativeTrendItem } from "../api";

function getCategoryColor(category: string | null): string {
  if (!category) return "#94a3b8";
  const c = category.toLowerCase();
  if (c.includes("war") || c.includes("conflict") || c.includes("military")) return "#ef4444";
  if (c.includes("election") || c.includes("democracy") || c.includes("political")) return "#f59e0b";
  if (c.includes("health") || c.includes("bio") || c.includes("pandemic")) return "#10b981";
  if (c.includes("cyber") || c.includes("tech") || c.includes("ai")) return "#3b82f6";
  if (c.includes("climate") || c.includes("environment")) return "#06b6d4";
  return "#8b5cf6";
}

function NarrativeRow({ item, maxMatches }: { item: NarrativeTrendItem; maxMatches: number }) {
  const color = getCategoryColor(item.category);
  const pct = maxMatches > 0 ? (item.total_matches / maxMatches) * 100 : 0;
  const total = item.confidence_high + item.confidence_medium + item.confidence_low;

  return (
    <Box
      sx={{
        py: 1,
        px: 1.5,
        borderBottom: "1px solid rgba(148,163,184,0.06)",
        "&:last-child": { borderBottom: "none" },
        "&:hover": { backgroundColor: "rgba(255,255,255,0.02)" },
        transition: "background 0.15s ease",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 0.5 }}>
        <Typography
          variant="caption"
          fontWeight={700}
          sx={{
            fontSize: "0.72rem",
            lineHeight: 1.3,
            display: "-webkit-box",
            WebkitLineClamp: 1,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            flex: 1,
            pr: 1,
          }}
        >
          {item.narrative_name}
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexShrink: 0 }}>
          <Typography
            variant="caption"
            sx={{ fontSize: "0.65rem", fontWeight: 800, color }}
          >
            {item.total_matches}
          </Typography>
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.6rem" }}>
            hits
          </Typography>
        </Box>
      </Box>

      {/* Progress bar */}
      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{
          height: 3,
          borderRadius: 2,
          mb: 0.5,
          backgroundColor: "rgba(255,255,255,0.05)",
          "& .MuiLinearProgress-bar": {
            backgroundColor: color,
            borderRadius: 2,
          },
        }}
      />

      {/* Meta row */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
        {item.category && (
          <Chip
            label={item.category}
            size="small"
            sx={{
              height: 14,
              fontSize: "0.55rem",
              fontWeight: 700,
              backgroundColor: `${color}18`,
              color: color,
              border: `1px solid ${color}33`,
              "& .MuiChip-label": { px: 0.5 },
            }}
          />
        )}
        <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.62rem" }}>
          {item.report_count} reports
        </Typography>
        {/* Confidence breakdown dots */}
        {total > 0 && (
          <Box sx={{ display: "flex", gap: 0.25, ml: "auto" }}>
            {item.confidence_high > 0 && (
              <Chip
                label={`H:${item.confidence_high}`}
                size="small"
                sx={{ height: 14, fontSize: "0.52rem", backgroundColor: "rgba(239,68,68,0.12)", color: "#ef4444", "& .MuiChip-label": { px: 0.5 } }}
              />
            )}
            {item.confidence_medium > 0 && (
              <Chip
                label={`M:${item.confidence_medium}`}
                size="small"
                sx={{ height: 14, fontSize: "0.52rem", backgroundColor: "rgba(245,158,11,0.12)", color: "#f59e0b", "& .MuiChip-label": { px: 0.5 } }}
              />
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
}

export const NarrativeTrendPanel = () => {
  const { data: trends, isLoading } = useQuery({
    queryKey: ["narrative-trends"],
    queryFn: fetchNarrativeTrends,
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });

  const maxMatches = trends ? Math.max(...trends.map((t) => t.total_matches), 1) : 1;

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
          <TrendingUpIcon sx={{ fontSize: 16, color: "#8b5cf6" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Active Narratives
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          {trends?.length ?? 0} tracked
        </Typography>
      </Box>

      {/* List */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          "&::-webkit-scrollbar": { width: 4 },
          "&::-webkit-scrollbar-thumb": { backgroundColor: "rgba(148,163,184,0.2)", borderRadius: 2 },
        }}
      >
        {isLoading &&
          Array.from({ length: 6 }).map((_, i) => (
            <Box key={i} sx={{ px: 1.5, py: 1, borderBottom: "1px solid rgba(148,163,184,0.06)" }}>
              <Skeleton variant="text" width="70%" height={14} sx={{ mb: 0.5 }} />
              <Skeleton variant="rectangular" height={3} sx={{ borderRadius: 2, mb: 0.5 }} />
              <Skeleton variant="text" width="40%" height={12} />
            </Box>
          ))}

        {!isLoading && (!trends || trends.length === 0) && (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
              No narratives detected yet
            </Typography>
            <Typography variant="caption" color="text.disabled">
              Complete analyses to see narrative trends
            </Typography>
          </Box>
        )}

        {trends?.map((item) => (
          <NarrativeRow key={item.narrative_id} item={item} maxMatches={maxMatches} />
        ))}
      </Box>
    </Box>
  );
};
