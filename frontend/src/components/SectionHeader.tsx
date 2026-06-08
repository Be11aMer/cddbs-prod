import { Box, Typography, Chip } from "@mui/material";
import type { ReactNode } from "react";

interface Props {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  /** Accent color tying this section to its stage in the pipeline narrative */
  accentColor: string;
  /** e.g. "3 events need review" — surfaces what needs analyst attention */
  badge?: string | number;
}

/**
 * Shared section-title primitive used across all six pipeline stages.
 * Each stage gets a distinct accent color so an analyst's eye can jump
 * straight to the part of the chain that matters right now.
 */
export const SectionHeader = ({ icon, title, subtitle, accentColor, badge }: Props) => (
  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
    <Box
      sx={{
        width: 36,
        height: 36,
        borderRadius: 2,
        backgroundColor: `${accentColor}1a`,
        border: `1px solid ${accentColor}33`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        color: accentColor,
      }}
    >
      {icon}
    </Box>
    <Box sx={{ minWidth: 0, flex: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.2, fontSize: "1.05rem" }}>
          {title}
        </Typography>
        {badge != null && badge !== "" && (
          <Chip
            label={badge}
            size="small"
            sx={{
              height: 18,
              fontSize: "0.65rem",
              fontWeight: 800,
              backgroundColor: `${accentColor}1a`,
              color: accentColor,
              border: `1px solid ${accentColor}44`,
              "& .MuiChip-label": { px: 0.9 },
            }}
          />
        )}
      </Box>
      {subtitle && (
        <Typography variant="caption" color="text.secondary" sx={{ display: { xs: "none", sm: "block" } }}>
          {subtitle}
        </Typography>
      )}
    </Box>
  </Box>
);
