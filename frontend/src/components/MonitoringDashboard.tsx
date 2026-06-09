import { Box, Grid, Skeleton } from "@mui/material";
import RadarIcon from "@mui/icons-material/Radar";
import { useQuery } from "@tanstack/react-query";
import { fetchGlobalStats, fetchStatsByCountry, fetchEventClusters } from "../api";
import { GlobalMap } from "./GlobalMap";
import { IntelFeed } from "./IntelFeed";
import { EventClusterPanel } from "./EventClusterPanel";
import { CollectorStatusBar } from "./CollectorStatusBar";
import { ActivityTimeline } from "./ActivityTimeline";
import { OpsHealthStrip } from "./OpsHealthStrip";
import { SectionHeader } from "./SectionHeader";
import { SEVERITY_COLORS } from "../utils/severity";
import type { ViewType } from "../App";
import type { EventScope } from "./OutletNetworkGraph";

const EXPLOITATION_THRESHOLD = 0.4;

interface Props {
  /** Lets event-detail drill-ins jump straight into a downstream pipeline
   * stage, optionally carrying the event as scope context (real cluster FK). */
  onNavigate?: (view: ViewType, scope?: EventScope) => void;
  /** When set, EventClusterPanel auto-opens this event's detail dialog —
   * used when navigating back from a burst row to its originating event. */
  openEventId?: number | null;
  onEventOpened?: () => void;
}

/**
 * Stage 1 of the pipeline narrative: "Real-world events we're watching."
 * This is the anchor/lead view — everything else in the dashboard (exploitation
 * detection, auto-analysis, amplification tracking, narrative trends,
 * countermeasures) exists to answer "what's happening with THESE events."
 */
export const MonitoringDashboard = ({ onNavigate, openEventId, onEventOpened }: Props) => {
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

  // Shares its cache with EventClusterPanel's own query (same key + fetcher) —
  // used here only to compute the "exploitation flags" count for the ops strip.
  const { data: events } = useQuery({
    queryKey: ["event-clusters"],
    queryFn: () => fetchEventClusters({ status: "active", limit: 50 }),
    refetchInterval: 30 * 1000,
    staleTime: 15 * 1000,
  });
  const exploitedCount = (events ?? []).filter((e) => e.narrative_risk_score >= EXPLOITATION_THRESHOLD).length;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, height: "100%" }}>
      {/* Page header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5, flexWrap: "wrap" }}>
        <SectionHeader
          icon={<RadarIcon sx={{ fontSize: 20 }} />}
          title="Real-World Events"
          subtitle="What we're watching — every other stage of the pipeline traces back to these events"
          accentColor={SEVERITY_COLORS.info}
        />
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: "auto" }}>
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
            <Box component="span" sx={{ color: "#10b981", fontWeight: 700, fontSize: "0.7rem" }}>
              LIVE
            </Box>
          </Box>
        </Box>
      </Box>

      {/* Operational status strip — replaces the old 6-card vanity metric grid.
          Only operationally meaningful counts: what's active, what needs attention. */}
      <OpsHealthStrip stats={globalStats} isLoading={statsLoading} exploitedCount={exploitedCount} />

      {/* Lead content: Event Clusters (the anchor) + live Intel Feed */}
      <Grid container spacing={2} sx={{ flexGrow: 1 }}>
        <Grid item xs={12} lg={7}>
          <Box sx={{ height: { xs: 420, lg: 480 } }}>
            <EventClusterPanel
              onNavigate={onNavigate}
              openEventId={openEventId}
              onEventOpened={onEventOpened}
            />
          </Box>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Box sx={{ height: { xs: 360, lg: 480 } }}>
            <IntelFeed />
          </Box>
        </Grid>
      </Grid>

      {/* Supporting geo/temporal context — demoted from headline cards to
          background context for the events above */}
      <Grid container spacing={2}>
        <Grid item xs={12} lg={8}>
          <Box sx={{ height: { xs: 320, md: 360 } }}>
            {countryLoading ? (
              <Skeleton variant="rectangular" height="100%" sx={{ borderRadius: 3, backgroundColor: "rgba(255,255,255,0.04)" }} />
            ) : (
              <GlobalMap countryStats={countryStats ?? []} />
            )}
          </Box>
        </Grid>
        <Grid item xs={12} lg={4}>
          <Box sx={{ height: { xs: 320, md: 360 } }}>
            <ActivityTimeline />
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
