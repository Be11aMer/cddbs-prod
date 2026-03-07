import {
  Box,
  Typography,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  Link,
} from "@mui/material";
import BubbleChartIcon from "@mui/icons-material/BubbleChart";
import RefreshIcon from "@mui/icons-material/Refresh";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import CloseIcon from "@mui/icons-material/Close";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  fetchEventClusters,
  fetchEventDetail,
  type EventClusterItem,
  type EventClusterDetail,
} from "../api";

const EVENT_TYPE_COLORS: Record<string, string> = {
  conflict: "#ef4444",
  protest: "#f59e0b",
  diplomacy: "#3b82f6",
  disaster: "#8b5cf6",
  cyber: "#06b6d4",
  info_warfare: "#ec4899",
  economic: "#10b981",
  other: "#94a3b8",
};

function getRiskColor(score: number): string {
  if (score >= 0.7) return "#ef4444";
  if (score >= 0.4) return "#f59e0b";
  return "#10b981";
}

function EventRow({
  event,
  onClick,
}: {
  event: EventClusterItem;
  onClick: () => void;
}) {
  const typeColor = EVENT_TYPE_COLORS[event.event_type || "other"] || "#94a3b8";
  const riskColor = getRiskColor(event.narrative_risk_score);

  return (
    <Box
      onClick={onClick}
      sx={{
        py: 1.25,
        px: 1.5,
        borderBottom: "1px solid rgba(148,163,184,0.07)",
        cursor: "pointer",
        transition: "background 0.15s ease",
        "&:hover": { backgroundColor: "rgba(255,255,255,0.03)" },
        "&:last-child": { borderBottom: "none" },
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 1,
          mb: 0.5,
        }}
      >
        <Typography
          variant="body2"
          fontWeight={600}
          sx={{
            fontSize: "0.78rem",
            lineHeight: 1.35,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            flexGrow: 1,
          }}
        >
          {event.title || "Unnamed event"}
        </Typography>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.5,
            flexShrink: 0,
          }}
        >
          <Typography
            variant="caption"
            fontWeight={700}
            sx={{ color: riskColor, fontSize: "0.7rem" }}
          >
            {(event.narrative_risk_score * 100).toFixed(0)}%
          </Typography>
        </Box>
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flexWrap: "wrap" }}>
        <Chip
          label={event.event_type || "other"}
          size="small"
          sx={{
            height: 14,
            fontSize: "0.55rem",
            fontWeight: 800,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            backgroundColor: `${typeColor}22`,
            color: typeColor,
            border: `1px solid ${typeColor}44`,
            "& .MuiChip-label": { px: 0.75 },
          }}
        />
        <Typography
          variant="caption"
          color="text.disabled"
          sx={{ fontSize: "0.65rem" }}
        >
          {event.article_count} articles
        </Typography>
        <Typography
          variant="caption"
          color="text.disabled"
          sx={{ fontSize: "0.65rem" }}
        >
          {event.source_count} sources
        </Typography>
        {event.countries && event.countries.length > 0 && (
          <Typography
            variant="caption"
            color="text.disabled"
            sx={{ fontSize: "0.65rem", ml: "auto" }}
          >
            {event.countries.slice(0, 2).join(", ")}
            {event.countries.length > 2 && ` +${event.countries.length - 2}`}
          </Typography>
        )}
      </Box>

      <LinearProgress
        variant="determinate"
        value={event.narrative_risk_score * 100}
        sx={{
          mt: 0.75,
          height: 2,
          borderRadius: 1,
          backgroundColor: "rgba(148,163,184,0.1)",
          "& .MuiLinearProgress-bar": {
            backgroundColor: riskColor,
            borderRadius: 1,
          },
        }}
      />
    </Box>
  );
}

function EventDetailDialog({
  eventId,
  open,
  onClose,
}: {
  eventId: number | null;
  open: boolean;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["event-detail", eventId],
    queryFn: () => fetchEventDetail(eventId!),
    enabled: open && eventId !== null,
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography variant="h6" fontWeight={700} sx={{ fontSize: "1rem" }}>
          Event Detail
        </Typography>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        {data && (
          <Box>
            <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>
              {data.title}
            </Typography>
            <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
              {data.event_type && (
                <Chip
                  label={data.event_type}
                  size="small"
                  sx={{
                    backgroundColor: `${EVENT_TYPE_COLORS[data.event_type] || "#94a3b8"}22`,
                    color: EVENT_TYPE_COLORS[data.event_type] || "#94a3b8",
                  }}
                />
              )}
              <Chip
                label={`Risk: ${(data.narrative_risk_score * 100).toFixed(0)}%`}
                size="small"
                sx={{
                  backgroundColor: `${getRiskColor(data.narrative_risk_score)}22`,
                  color: getRiskColor(data.narrative_risk_score),
                }}
              />
              <Chip label={`${data.article_count} articles`} size="small" variant="outlined" />
              <Chip label={`${data.source_count} sources`} size="small" variant="outlined" />
            </Box>

            {data.keywords && data.keywords.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={700}>
                  Keywords
                </Typography>
                <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.5 }}>
                  {data.keywords.map((kw) => (
                    <Chip key={kw} label={kw} size="small" variant="outlined" sx={{ height: 20, fontSize: "0.65rem" }} />
                  ))}
                </Box>
              </Box>
            )}

            <Typography variant="caption" color="text.secondary" fontWeight={700} sx={{ mb: 1, display: "block" }}>
              Articles ({data.articles.length})
            </Typography>
            {data.articles.map((a, i) => (
              <Box
                key={a.id || i}
                sx={{
                  py: 0.75,
                  borderBottom: "1px solid rgba(148,163,184,0.1)",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 1,
                }}
              >
                <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                  <Link
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    underline="hover"
                    sx={{ fontSize: "0.8rem", fontWeight: 600 }}
                  >
                    {a.title}
                  </Link>
                  <Box sx={{ display: "flex", gap: 1, mt: 0.25 }}>
                    <Typography variant="caption" color="text.disabled">
                      {a.source_name}
                    </Typography>
                    <Chip
                      label={a.source_type}
                      size="small"
                      sx={{ height: 14, fontSize: "0.5rem", fontWeight: 700 }}
                    />
                    {a.published_at && (
                      <Typography variant="caption" color="text.disabled">
                        {new Date(a.published_at).toLocaleString()}
                      </Typography>
                    )}
                  </Box>
                </Box>
                <IconButton
                  component="a"
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="small"
                  sx={{ p: 0.25, color: "text.disabled", flexShrink: 0 }}
                >
                  <OpenInNewIcon sx={{ fontSize: 12 }} />
                </IconButton>
              </Box>
            ))}
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}

export const EventClusterPanel = () => {
  const [selectedEvent, setSelectedEvent] = useState<number | null>(null);
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["event-clusters"],
    queryFn: () => fetchEventClusters({ status: "active", limit: 20 }),
    refetchInterval: 30 * 1000,
    staleTime: 15 * 1000,
  });

  const events = data ?? [];

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
            <BubbleChartIcon sx={{ fontSize: 16, color: "#8b5cf6" }} />
            <Typography variant="subtitle2" fontWeight={700}>
              Event Clusters
            </Typography>
            {events.length > 0 && (
              <Chip
                label={events.length}
                size="small"
                sx={{
                  height: 16,
                  fontSize: "0.6rem",
                  fontWeight: 700,
                  backgroundColor: "rgba(139,92,246,0.1)",
                  color: "#8b5cf6",
                  "& .MuiChip-label": { px: 0.75 },
                }}
              />
            )}
          </Box>
          <Tooltip title="Refresh events">
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

        {/* Event list */}
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
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                gap: 1.5,
              }}
            >
              <CircularProgress size={20} />
              <Typography variant="body2" color="text.secondary">
                Loading events...
              </Typography>
            </Box>
          )}

          {!isLoading && events.length === 0 && (
            <Box sx={{ p: 3, textAlign: "center" }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                No event clusters detected yet
              </Typography>
              <Typography variant="caption" color="text.disabled">
                Events will appear as the collector pipeline processes articles
              </Typography>
            </Box>
          )}

          {events.map((event) => (
            <EventRow
              key={event.id}
              event={event}
              onClick={() => setSelectedEvent(event.id)}
            />
          ))}
        </Box>
      </Box>

      <EventDetailDialog
        eventId={selectedEvent}
        open={selectedEvent !== null}
        onClose={() => setSelectedEvent(null)}
      />
    </>
  );
};
