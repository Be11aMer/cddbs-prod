import { Box, Grid, Typography, Skeleton } from "@mui/material";
import RadarIcon from "@mui/icons-material/Radar";
import PublicIcon from "@mui/icons-material/Public";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PlayCircleIcon from "@mui/icons-material/PlayCircle";
import BubbleChartIcon from "@mui/icons-material/BubbleChart";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import StorageIcon from "@mui/icons-material/Storage";
import { useQuery } from "@tanstack/react-query";
import { fetchGlobalStats, fetchStatsByCountry } from "../api";
import { GlobalMap } from "./GlobalMap";
import { IntelFeed } from "./IntelFeed";
import { NarrativeTrendPanel } from "./NarrativeTrendPanel";
import { CountryRiskIndex } from "./CountryRiskIndex";
import { EventClusterPanel } from "./EventClusterPanel";
import { CollectorStatusBar } from "./CollectorStatusBar";
import { MetricCard } from "./MetricCard";
import { MetricCardSkeleton } from "./Skeletons";
import { ActivityTimeline } from "./ActivityTimeline";
import { NarrativeBarChart } from "./NarrativeBarChart";

export const MonitoringDashboard = () => {
  const { data: globalStats, isLoading: statsLoading } = useQuery({
    queryKey: ["global-stats"],
    queryFn: fetchGlobalStats,
    refetchInterval: 15 * 1000,
    staleTime: 10 * 1000,
  });

  const { data: countryStats, isLoading: countryLoading } = useQuery({
    queryKey: ["stats-by-country"],
    queryFn: fetchStatsByCountry,
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, height: "100%" }}>
      {/* Page header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5, flexWrap: "wrap" }}>
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: 2,
            backgroundColor: "rgba(59,130,246,0.1)",
            border: "1px solid rgba(59,130,246,0.2)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <RadarIcon sx={{ fontSize: 20, color: "primary.main" }} />
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.2 }}>
            Global Monitoring
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: { xs: "none", sm: "block" } }}>
            Real-time disinformation intelligence · Multi-source event detection
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CollectorStatusBar />
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.75,
              px: 1.5,
              py: 0.5,
              borderRadius: 2,
              backgroundColor: "rgba(16,185,129,0.08)",
              border: "1px solid rgba(16,185,129,0.2)",
            }}
          >
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "#10b981",
                animation: "pulse-opacity 2s infinite",
              }}
            />
            <Typography variant="caption" fontWeight={700} sx={{ color: "#10b981", fontSize: "0.7rem" }}>
              LIVE
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Metric cards row — 6 cards */}
      <Grid container spacing={2}>
        <Grid item xs={6} sm={4} md={2}>
          {statsLoading ? (
            <MetricCardSkeleton />
          ) : (
            <MetricCard
              title="Articles Ingested"
              value={globalStats?.articles_ingested ?? 0}
              icon={<StorageIcon sx={{ fontSize: 24 }} />}
              color="info"
              tooltip="Total articles collected from RSS feeds and GDELT"
            />
          )}
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          {statsLoading ? (
            <MetricCardSkeleton />
          ) : (
            <MetricCard
              title="Active Events"
              value={globalStats?.active_events ?? 0}
              icon={<BubbleChartIcon sx={{ fontSize: 24 }} />}
              color={(globalStats?.active_events ?? 0) > 0 ? "warning" : "success"}
              tooltip="Detected event clusters currently active"
            />
          )}
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          {statsLoading ? (
            <MetricCardSkeleton />
          ) : (
            <MetricCard
              title="Narrative Bursts"
              value={globalStats?.active_bursts ?? 0}
              icon={<TrendingUpIcon sx={{ fontSize: 24 }} />}
              color={(globalStats?.active_bursts ?? 0) > 0 ? "error" : "success"}
              tooltip="Active keyword frequency spikes (z-score > 3)"
            />
          )}
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          {statsLoading ? (
            <MetricCardSkeleton />
          ) : (
            <MetricCard
              title="Countries"
              value={globalStats?.countries_monitored ?? 0}
              icon={<PublicIcon sx={{ fontSize: 24 }} />}
              color="info"
              tooltip="Unique countries with at least one completed analysis"
            />
          )}
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          {statsLoading ? (
            <MetricCardSkeleton />
          ) : (
            <MetricCard
              title="Narratives"
              value={globalStats?.total_narratives_detected ?? 0}
              icon={<WarningAmberIcon sx={{ fontSize: 24 }} />}
              color={
                (globalStats?.total_narratives_detected ?? 0) > 0 ? "warning" : "success"
              }
              tooltip="Total disinformation narrative hits across all analyses"
            />
          )}
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          {statsLoading ? (
            <MetricCardSkeleton />
          ) : (
            <MetricCard
              title="Analyses"
              value={globalStats?.total_analyses ?? 0}
              icon={<PlayCircleIcon sx={{ fontSize: 24 }} />}
              color="info"
              tooltip="Total intelligence reports generated"
            />
          )}
        </Grid>
      </Grid>

      {/* Main content: Map + Intel Feed */}
      <Grid container spacing={2} sx={{ flexGrow: 1 }}>
        {/* World Map */}
        <Grid item xs={12} lg={8}>
          <Box sx={{ height: { xs: 320, md: 380, lg: 420 } }}>
            {countryLoading ? (
              <Skeleton
                variant="rectangular"
                height="100%"
                sx={{ borderRadius: 3, backgroundColor: "rgba(255,255,255,0.04)" }}
              />
            ) : (
              <GlobalMap countryStats={countryStats ?? []} />
            )}
          </Box>
        </Grid>

        {/* Intel Feed */}
        <Grid item xs={12} lg={4}>
          <Box sx={{ height: { xs: 360, md: 380, lg: 420 } }}>
            <IntelFeed />
          </Box>
        </Grid>
      </Grid>

      {/* v1.2 Charts: Activity Timeline + Narrative Bar Chart */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <Box sx={{ height: 280 }}>
            <ActivityTimeline />
          </Box>
        </Grid>
        <Grid item xs={12} md={5}>
          <Box sx={{ height: 280 }}>
            <NarrativeBarChart />
          </Box>
        </Grid>
      </Grid>

      {/* Bottom row: Event Clusters + Narrative Trends + Country Risk */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Box sx={{ height: 360 }}>
            <EventClusterPanel />
          </Box>
        </Grid>
        <Grid item xs={12} md={4}>
          <Box sx={{ height: 360 }}>
            <NarrativeTrendPanel />
          </Box>
        </Grid>
        <Grid item xs={12} md={4}>
          <Box sx={{ height: 360 }}>
            <CountryRiskIndex />
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
