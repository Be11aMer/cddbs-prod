import { Box, Grid } from "@mui/material";
import TimelineIcon from "@mui/icons-material/Timeline";
import { NarrativeTrendPanel } from "./NarrativeTrendPanel";
import { CountryRiskIndex } from "./CountryRiskIndex";
import { SectionHeader } from "./SectionHeader";
import { SEVERITY_COLORS } from "../utils/severity";

/**
 * Stage 5 of the pipeline narrative: how the exploitation has spread, persisted,
 * or decayed since the originating events — which narratives dominate, with
 * what confidence, and where (geographically) the risk is concentrated.
 */
export const NarrativeTrendSection = () => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, height: "100%" }}>
    <SectionHeader
      icon={<TimelineIcon sx={{ fontSize: 20 }} />}
      title="Narrative Trend &amp; Evolution"
      subtitle="How the exploitation has spread, persisted, or decayed since the originating events"
      accentColor={SEVERITY_COLORS.accent}
    />
    <Grid container spacing={2} sx={{ flexGrow: 1 }}>
      <Grid item xs={12} lg={7}>
        <Box sx={{ height: { xs: 480, lg: 580 } }}>
          <NarrativeTrendPanel />
        </Box>
      </Grid>
      <Grid item xs={12} lg={5}>
        <Box sx={{ height: { xs: 480, lg: 580 } }}>
          <CountryRiskIndex />
        </Box>
      </Grid>
    </Grid>
  </Box>
);
