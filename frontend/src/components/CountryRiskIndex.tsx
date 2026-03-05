import { Box, Typography, Chip, Skeleton } from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";
import { useQuery } from "@tanstack/react-query";
import { fetchStatsByCountry, type CountryStatItem } from "../api";

function getRiskColor(score: number): string {
  if (score >= 60) return "#ef4444";
  if (score >= 30) return "#f59e0b";
  if (score > 0) return "#3b82f6";
  return "#94a3b8";
}

function getRiskLabel(score: number): string {
  if (score >= 60) return "HIGH";
  if (score >= 30) return "ELEVATED";
  if (score > 0) return "LOW";
  return "NONE";
}

function CountryRow({ item, rank, maxScore }: { item: CountryStatItem; rank: number; maxScore: number }) {
  const color = getRiskColor(item.risk_score);
  const pct = maxScore > 0 ? (item.risk_score / maxScore) * 100 : 0;

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        py: 0.875,
        px: 2,
        borderBottom: "1px solid rgba(148,163,184,0.06)",
        "&:last-child": { borderBottom: "none" },
        "&:hover": { backgroundColor: "rgba(255,255,255,0.025)" },
        transition: "background 0.15s ease",
      }}
    >
      {/* Rank */}
      <Typography
        variant="caption"
        sx={{
          fontSize: "0.65rem",
          fontWeight: 700,
          color: rank <= 3 ? color : "text.disabled",
          width: 20,
          textAlign: "center",
          flexShrink: 0,
        }}
      >
        {rank}
      </Typography>

      {/* Country + bar */}
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 0.3 }}>
          <Typography variant="caption" fontWeight={700} sx={{ fontSize: "0.75rem" }}>
            {item.country}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.62rem" }}>
              {item.narrative_count} narr · {item.run_count} runs
            </Typography>
            <Chip
              label={getRiskLabel(item.risk_score)}
              size="small"
              sx={{
                height: 14,
                fontSize: "0.52rem",
                fontWeight: 800,
                letterSpacing: "0.04em",
                backgroundColor: `${color}18`,
                color,
                border: `1px solid ${color}33`,
                "& .MuiChip-label": { px: 0.5 },
              }}
            />
          </Box>
        </Box>
        {/* Progress bar */}
        <Box
          sx={{
            height: 2.5,
            borderRadius: 2,
            backgroundColor: "rgba(255,255,255,0.05)",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              height: "100%",
              width: `${pct}%`,
              backgroundColor: color,
              borderRadius: 2,
              transition: "width 0.6s cubic-bezier(0.4,0,0.2,1)",
              boxShadow: rank <= 3 ? `0 0 6px ${color}88` : "none",
            }}
          />
        </Box>
      </Box>
    </Box>
  );
}

export const CountryRiskIndex = () => {
  const { data: countries, isLoading } = useQuery({
    queryKey: ["stats-by-country"],
    queryFn: fetchStatsByCountry,
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });

  const maxScore = countries ? Math.max(...countries.map((c) => c.risk_score), 1) : 1;
  const highCount = countries?.filter((c) => c.risk_score >= 60).length ?? 0;

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
          <LanguageIcon sx={{ fontSize: 16, color: "#10b981" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Country Risk Index
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
          {highCount > 0 && (
            <Chip
              label={`${highCount} HIGH`}
              size="small"
              sx={{
                height: 16,
                fontSize: "0.55rem",
                fontWeight: 800,
                backgroundColor: "rgba(239,68,68,0.12)",
                color: "#ef4444",
                border: "1px solid rgba(239,68,68,0.25)",
              }}
            />
          )}
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
            {countries?.length ?? 0} countries
          </Typography>
        </Box>
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
          Array.from({ length: 8 }).map((_, i) => (
            <Box key={i} sx={{ px: 2, py: 0.875, borderBottom: "1px solid rgba(148,163,184,0.06)", display: "flex", gap: 1.5, alignItems: "center" }}>
              <Skeleton variant="text" width={20} height={14} />
              <Box sx={{ flexGrow: 1 }}>
                <Skeleton variant="text" width="60%" height={14} sx={{ mb: 0.3 }} />
                <Skeleton variant="rectangular" height={2.5} sx={{ borderRadius: 2 }} />
              </Box>
            </Box>
          ))}

        {!isLoading && (!countries || countries.length === 0) && (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
              No country data yet
            </Typography>
            <Typography variant="caption" color="text.disabled">
              Run analyses to populate the risk index
            </Typography>
          </Box>
        )}

        {countries?.map((item, i) => (
          <CountryRow key={item.country} item={item} rank={i + 1} maxScore={maxScore} />
        ))}
      </Box>
    </Box>
  );
};
