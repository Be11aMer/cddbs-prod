import { Box, Typography, Chip, IconButton, Tooltip, CircularProgress, Link } from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import RssFeedIcon from "@mui/icons-material/RssFeed";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useQuery } from "@tanstack/react-query";
import { fetchMonitoringFeed, type FeedItem } from "../api";

function getUrgencyColor(title: string): { color: string; label: string } {
  const t = title.toLowerCase();
  if (
    t.includes("attack") || t.includes("missile") || t.includes("war") ||
    t.includes("crisis") || t.includes("emergency") || t.includes("explosion") ||
    t.includes("killed") || t.includes("bomb")
  ) {
    return { color: "#ef4444", label: "BREAKING" };
  }
  if (
    t.includes("disinformation") || t.includes("propaganda") || t.includes("fake") ||
    t.includes("misinformation") || t.includes("manipulation") || t.includes("interference")
  ) {
    return { color: "#f59e0b", label: "DISINFO" };
  }
  if (
    t.includes("election") || t.includes("cyber") || t.includes("hack") ||
    t.includes("intelligence") || t.includes("espionage") || t.includes("sanction")
  ) {
    return { color: "#3b82f6", label: "INTEL" };
  }
  return { color: "#94a3b8", label: "NEWS" };
}

function formatTimeAgo(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const diffMs = Date.now() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    return `${Math.floor(diffHrs / 24)}d ago`;
  } catch {
    return "";
  }
}

function FeedItemRow({ item }: { item: FeedItem }) {
  const { color, label } = getUrgencyColor(item.title);

  return (
    <Box
      sx={{
        py: 1.25,
        px: 1.5,
        borderBottom: "1px solid rgba(148,163,184,0.07)",
        display: "flex",
        gap: 1.25,
        alignItems: "flex-start",
        transition: "background 0.15s ease",
        "&:hover": {
          backgroundColor: "rgba(255,255,255,0.03)",
          cursor: "pointer",
        },
        "&:last-child": { borderBottom: "none" },
      }}
    >
      {/* Urgency dot */}
      <Box
        sx={{
          mt: 0.6,
          width: 7,
          height: 7,
          borderRadius: "50%",
          backgroundColor: color,
          flexShrink: 0,
          boxShadow: label === "BREAKING" ? `0 0 6px ${color}` : "none",
          animation: label === "BREAKING" ? "pulse-opacity 1.5s infinite" : "none",
        }}
      />

      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 0.5, mb: 0.25 }}>
          <Link
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            underline="none"
            sx={{
              color: "text.primary",
              fontWeight: 600,
              fontSize: "0.78rem",
              lineHeight: 1.35,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              "&:hover": { color: "primary.light" },
              flexGrow: 1,
            }}
          >
            {item.title}
          </Link>
          <IconButton
            component="a"
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            size="small"
            sx={{ p: 0.25, color: "text.disabled", flexShrink: 0, mt: 0.2 }}
          >
            <OpenInNewIcon sx={{ fontSize: 12 }} />
          </IconButton>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flexWrap: "wrap" }}>
          <Chip
            label={label}
            size="small"
            sx={{
              height: 14,
              fontSize: "0.55rem",
              fontWeight: 800,
              letterSpacing: "0.05em",
              backgroundColor: `${color}22`,
              color: color,
              border: `1px solid ${color}44`,
              "& .MuiChip-label": { px: 0.75 },
            }}
          />
          {item.domain && (
            <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.65rem" }}>
              {item.domain}
            </Typography>
          )}
          {item.source_country && (
            <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.65rem" }}>
              · {item.source_country}
            </Typography>
          )}
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.65rem", ml: "auto" }}>
            {formatTimeAgo(item.published)}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}

export const IntelFeed = () => {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["monitoring-feed"],
    queryFn: fetchMonitoringFeed,
    refetchInterval: 5 * 60 * 1000, // refresh every 5 min
    staleTime: 3 * 60 * 1000,
  });

  const items = data?.items ?? [];

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
          <RssFeedIcon sx={{ fontSize: 16, color: "#f59e0b" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Intel Feed
          </Typography>
          <Chip
            label={data?.source?.includes("SerpAPI") ? "SerpAPI" : "GDELT"}
            size="small"
            sx={{
              height: 16,
              fontSize: "0.55rem",
              fontWeight: 700,
              backgroundColor: "rgba(245,158,11,0.1)",
              color: "#f59e0b",
              border: "1px solid rgba(245,158,11,0.2)",
              "& .MuiChip-label": { px: 0.75 },
            }}
          />
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {items.length > 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
              {items.length} articles
            </Typography>
          )}
          <Tooltip title="Refresh feed">
            <span>
              <IconButton
                size="small"
                onClick={() => refetch()}
                disabled={isFetching}
                sx={{
                  color: "text.secondary",
                  "&:hover": { color: "primary.main" },
                }}
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
      </Box>

      {/* Feed list */}
      <Box sx={{ flexGrow: 1, overflowY: "auto", "&::-webkit-scrollbar": { width: 4 }, "&::-webkit-scrollbar-thumb": { backgroundColor: "rgba(148,163,184,0.2)", borderRadius: 2 } }}>
        {isLoading && (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", gap: 1.5 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">
              Loading intel feed...
            </Typography>
          </Box>
        )}

        {isError && !isLoading && (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Unable to load intel feed
            </Typography>
            <Typography variant="caption" color="text.disabled">
              Check backend connectivity
            </Typography>
          </Box>
        )}

        {!isLoading && !isError && items.length === 0 && (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75 }}>
              No articles available
            </Typography>
            <Typography variant="caption" color="text.disabled" sx={{ lineHeight: 1.5 }}>
              {data?.source?.startsWith("unavailable")
                ? data.source.replace("unavailable — ", "")
                : "Feed sources returned no results. Try refreshing."}
            </Typography>
          </Box>
        )}

        {items.map((item, i) => (
          <FeedItemRow key={`${item.url}-${i}`} item={item} />
        ))}
      </Box>

      {/* Footer */}
      {data && (
        <Box
          sx={{
            px: 2,
            py: 0.75,
            borderTop: "1px solid rgba(148,163,184,0.07)",
            flexShrink: 0,
          }}
        >
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.6rem" }}>
            Source: {data.source} · Updated {new Date(data.fetched_at).toLocaleTimeString()} · Auto-refreshes every 5 min
          </Typography>
        </Box>
      )}
    </Box>
  );
};
