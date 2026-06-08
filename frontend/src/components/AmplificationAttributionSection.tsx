import { Box, Grid } from "@mui/material";
import GroupsIcon from "@mui/icons-material/Groups";
import { OutletNetworkGraph } from "./OutletNetworkGraph";
import { SourceCredibilityPanel } from "./SourceCredibilityPanel";
import { SectionHeader } from "./SectionHeader";
import { SEVERITY_COLORS } from "../utils/severity";

/**
 * Stage 4 of the pipeline narrative: who is amplifying the narratives flagged
 * upstream — which outlets are coordinating, and how reliable each source is.
 * This is the "who" answer that the topic-analyst stage feeds into.
 */
export const AmplificationAttributionSection = () => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, height: "100%" }}>
    <SectionHeader
      icon={<GroupsIcon sx={{ fontSize: 20 }} />}
      title="Amplification &amp; Attribution"
      subtitle="Who is amplifying the flagged narratives — outlet coordination signals and source reliability"
      accentColor="#06b6d4"
    />
    <Grid container spacing={2} sx={{ flexGrow: 1 }}>
      <Grid item xs={12} lg={4}>
        <Box sx={{ height: { xs: 420, lg: 520 } }}>
          <SourceCredibilityPanel />
        </Box>
      </Grid>
      <Grid item xs={12} lg={8}>
        <Box sx={{ height: { xs: 420, lg: 520 } }}>
          <OutletNetworkGraph />
        </Box>
      </Grid>
    </Grid>
  </Box>
);
