import { Box, Typography, Skeleton } from "@mui/material";
import BarChartIcon from "@mui/icons-material/BarChart";
import { useQuery } from "@tanstack/react-query";
import { fetchNarrativeFrequency } from "../api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

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

function truncateLabel(name: string, maxLen = 20): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen - 1) + "…";
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: 2,
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        border: "1px solid rgba(148,163,184,0.2)",
        backdropFilter: "blur(8px)",
        maxWidth: 250,
      }}
    >
      <Typography variant="caption" fontWeight={700} display="block" sx={{ mb: 0.5 }}>
        {d.narrative_name}
      </Typography>
      {d.category && (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
          {d.category}
        </Typography>
      )}
      <Typography variant="caption" display="block">
        Total matches: <b>{d.total_matches}</b>
      </Typography>
      <Box sx={{ display: "flex", gap: 1, mt: 0.5 }}>
        {d.high > 0 && (
          <Typography variant="caption" sx={{ color: "#ef4444", fontWeight: 700 }}>
            H:{d.high}
          </Typography>
        )}
        {d.medium > 0 && (
          <Typography variant="caption" sx={{ color: "#f59e0b", fontWeight: 700 }}>
            M:{d.medium}
          </Typography>
        )}
        {d.low > 0 && (
          <Typography variant="caption" sx={{ color: "#94a3b8", fontWeight: 700 }}>
            L:{d.low}
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export const NarrativeBarChart = () => {
  const { data: narratives, isLoading } = useQuery({
    queryKey: ["narrative-frequency"],
    queryFn: () => fetchNarrativeFrequency(10),
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });

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
          <BarChartIcon sx={{ fontSize: 16, color: "#f59e0b" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Narrative Frequency
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          {narratives?.length ?? 0} narratives
        </Typography>
      </Box>

      {/* Chart */}
      <Box sx={{ flexGrow: 1, px: 1, py: 1, minHeight: 0 }}>
        {isLoading ? (
          <Skeleton variant="rectangular" height="100%" sx={{ borderRadius: 2, backgroundColor: "rgba(255,255,255,0.04)" }} />
        ) : !narratives || narratives.length === 0 ? (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <Typography variant="body2" color="text.secondary">No narrative data yet</Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={narratives}
              layout="vertical"
              margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 10, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="narrative_name"
                tickFormatter={(name: string) => truncateLabel(name)}
                tick={{ fontSize: 9, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                width={110}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Bar dataKey="total_matches" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {narratives.map((entry, index) => (
                  <Cell key={index} fill={getCategoryColor(entry.category)} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Box>
    </Box>
  );
};
