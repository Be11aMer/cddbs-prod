import { Box, Grid } from "@mui/material";
import GroupsIcon from "@mui/icons-material/Groups";
import { OutletNetworkGraph, type EventScope } from "./OutletNetworkGraph";
import { SourceCredibilityPanel } from "./SourceCredibilityPanel";
import { SectionHeader } from "./SectionHeader";
import { SEVERITY_COLORS } from "../utils/severity";

interface Props {
  /** When set, scopes both panels to outlets that covered this event
   * (real RawArticle.cluster_id FK on the backend). */
  scopedEvent?: EventScope | null;
  onClearScope?: () => void;
}

/**
 * Stage 4 of the pipeline narrative: who is amplifying the narratives flagged
 * upstream — which outlets are coordinating, and how reliable each source is.
 * This is the "who" answer that the topic-analyst stage feeds into.
 */
export const AmplificationAttributionSection = ({ scopedEvent, onClearScope }: Props = {}) => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, height: "100%" }}>
    <SectionHeader
      icon={<GroupsIcon sx={{ fontSize: 20 }} />}
      title="Amplification &amp; Attribution"
      subtitle={
        scopedEvent
          ? `Outlets amplifying "${scopedEvent.title}" — coordination signals and source reliability for this event`
          : "Who is amplifying the flagged narratives — outlet coordination signals and source reliability"
      }
      accentColor="#06b6d4"
    />
    <Grid container spacing={2} sx={{ flexGrow: 1 }}>
      <Grid item xs={12} lg={4}>
        <Box sx={{ height: { xs: 420, lg: 520 } }}>
          <SourceCredibilityPanel scopedEvent={scopedEvent} onClearScope={onClearScope} />
        </Box>
      </Grid>
      <Grid item xs={12} lg={8}>
        <Box sx={{ height: { xs: 420, lg: 520 } }}>
          <OutletNetworkGraph scopedEvent={scopedEvent} onClearScope={onClearScope} />
        </Box>
      </Grid>
    </Grid>
  </Box>
);
