import { Box, Typography, Chip, Tooltip, CircularProgress, IconButton } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import RefreshIcon from "@mui/icons-material/Refresh";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { useQuery } from "@tanstack/react-query";
import { fetchNarrativeBursts, type NarrativeBurstItem } from "../api";

function getZScoreColor(z: number | null): string {
  if (!z) return "#94a3b8";
  if (z >= 6) return "#ef4444";
  if (z >= 4) return "#f59e0b";
  return "#10b981";
}

function BurstRow({ burst }: { burst: NarrativeBurstItem }) {
  const z = burst.z_score ?? 0;
  const color = getZScoreColor(burst.z_score);
  const barWidth = Math.min((z / 10) * 100, 100);
  const detectedAt = burst.detected_at ? new Date(burst.detected_at) : null;

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
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, minWidth: 0, flex: 1 }}>
          <WarningAmberIcon sx={{ fontSize: 12, color, flexShrink: 0 }} />
          <Typography
            variant="caption"
            fontWeight={700}
            sx={{
              fontSize: "0.78rem",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {burst.keyword}
          </Typography>
        </Box>
        <Chip
          label={`z=${z.toFixed(1)}`}
          size="small"
          sx={{
            height: 16,
            fontSize: "0.6rem",
            fontWeight: 800,
            backgroundColor: `${color}22`,
            color,
            border: `1px solid ${color}44`,
            "& .MuiChip-label": { px: 0.5 },
            flexShrink: 0,
          }}
        />
      </Box>

      {/* Z-score bar */}
      <Box
        sx={{
          height: 3,
          borderRadius: 2,
          backgroundColor: "rgba(255,255,255,0.05)",
          overflow: "hidden",
          mb: 0.5,
        }}
      >
        <Box
          sx={{
            height: "100%",
            width: `${barWidth}%`,
            backgroundColor: color,
            borderRadius: 2,
            transition: "width 0.4s ease",
          }}
        />
      </Box>

      {/* Meta */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.6rem" }}>
          {burst.current_frequency ?? 0} articles/hr
        </Typography>
        <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.6rem" }}>
          baseline: {burst.baseline_frequency ?? 0}/hr
        </Typography>
        {detectedAt && (
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.6rem", ml: "auto" }}>
            {detectedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export const BurstTimeline = () => {
  const { data: bursts, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["narrative-bursts"],
    queryFn: fetchNarrativeBursts,
    refetchInterval: 30 * 1000,
    staleTime: 15 * 1000,
  });

  const activeBursts = bursts?.filter((b) => !b.resolved_at) ?? [];
  const sortedBursts = [...activeBursts].sort(
    (a, b) => (b.z_score ?? 0) - (a.z_score ?? 0)
  );

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
          <TrendingUpIcon sx={{ fontSize: 16, color: "#ef4444" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Narrative Bursts
          </Typography>
          {sortedBursts.length > 0 && (
            <Chip
              label={sortedBursts.length}
              size="small"
              sx={{
                height: 16,
                fontSize: "0.6rem",
                fontWeight: 700,
                backgroundColor: "rgba(239,68,68,0.1)",
                color: "#ef4444",
                "& .MuiChip-label": { px: 0.75 },
              }}
            />
          )}
        </Box>
        <Tooltip title="Refresh bursts">
          <span>
            <IconButton
              size="small"
              onClick={() => refetch()}
              disabled={isFetching}
              sx={{ color: "text.secondary", "&:hover": { color: "primary.main" } }}
            >
              {isFetching ? (
                <CircularProgress size={14} />
              ) : (
                <RefreshIcon sx={{ fontSize: 16 }} />
              )}
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      {/* Threshold indicator */}
      <Box
        sx={{
          px: 2,
          py: 0.5,
          backgroundColor: "rgba(239,68,68,0.04)",
          borderBottom: "1px solid rgba(148,163,184,0.06)",
          display: "flex",
          alignItems: "center",
          gap: 0.5,
        }}
      >
        <Box
          sx={{
            width: "100%",
            height: 1,
            backgroundColor: "rgba(239,68,68,0.3)",
            position: "relative",
          }}
        >
          <Typography
            variant="caption"
            sx={{
              position: "absolute",
              right: 0,
              top: -8,
              fontSize: "0.5rem",
              color: "rgba(239,68,68,0.6)",
              fontWeight: 700,
            }}
          >
            z=3.0 threshold
          </Typography>
        </Box>
      </Box>

      {/* Burst list */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          "&::-webkit-scrollbar": { width: 4 },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: "rgba(148,163,184,0.2)",
            borderRadius: 2,
          },
        }}
      >
        {isLoading && (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", gap: 1.5 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">
              Loading bursts...
            </Typography>
          </Box>
        )}

        {!isLoading && sortedBursts.length === 0 && (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
              No active narrative bursts
            </Typography>
            <Typography variant="caption" color="text.disabled">
              Bursts appear when keyword frequency exceeds z-score threshold
            </Typography>
          </Box>
        )}

        {sortedBursts.map((burst) => (
          <BurstRow key={burst.id} burst={burst} />
        ))}
      </Box>
    </Box>
  );
};
