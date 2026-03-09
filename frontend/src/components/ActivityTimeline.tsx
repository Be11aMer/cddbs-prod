import { Box, Typography, Skeleton } from "@mui/material";
import TimelineIcon from "@mui/icons-material/Timeline";
import { useQuery } from "@tanstack/react-query";
import { fetchActivityTimeline } from "../api";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

function formatHour(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function formatTick(iso: string): string {
  try {
    const d = new Date(iso);
    const h = d.getHours();
    if (h === 0) return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    return `${h}:00`;
  } catch {
    return "";
  }
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: 2,
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        border: "1px solid rgba(148,163,184,0.2)",
        backdropFilter: "blur(8px)",
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
        {formatHour(label)}
      </Typography>
      {payload.map((p: any) => (
        <Typography key={p.dataKey} variant="caption" display="block" sx={{ color: p.color, fontWeight: 700 }}>
          {p.name}: {p.value}
        </Typography>
      ))}
    </Box>
  );
};

export const ActivityTimeline = () => {
  const { data: timeline, isLoading } = useQuery({
    queryKey: ["activity-timeline"],
    queryFn: () => fetchActivityTimeline(48),
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });

  const totalArticles = timeline?.reduce((sum, b) => sum + b.count, 0) ?? 0;

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
          <TimelineIcon sx={{ fontSize: 16, color: "#3b82f6" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Ingestion Activity
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          {totalArticles} articles · 48h
        </Typography>
      </Box>

      {/* Chart */}
      <Box sx={{ flexGrow: 1, px: 1, py: 1, minHeight: 0 }}>
        {isLoading ? (
          <Skeleton variant="rectangular" height="100%" sx={{ borderRadius: 2, backgroundColor: "rgba(255,255,255,0.04)" }} />
        ) : !timeline || timeline.length === 0 ? (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <Typography variant="body2" color="text.secondary">No ingestion data yet</Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timeline} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradRss" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradGdelt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
              <XAxis
                dataKey="hour"
                tickFormatter={formatTick}
                tick={{ fontSize: 10, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="rss"
                name="RSS"
                stackId="1"
                stroke="#3b82f6"
                fill="url(#gradRss)"
                strokeWidth={1.5}
              />
              <Area
                type="monotone"
                dataKey="gdelt"
                name="GDELT"
                stackId="1"
                stroke="#10b981"
                fill="url(#gradGdelt)"
                strokeWidth={1.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Box>
    </Box>
  );
};
