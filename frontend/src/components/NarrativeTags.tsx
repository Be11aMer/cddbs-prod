import { Box, Chip, Typography, Stack, Tooltip } from "@mui/material";
import type { NarrativeMatchItem } from "../api";

const CATEGORY_COLORS: Record<string, string> = {
  "Anti-NATO / Western Alliance": "#ef4444",
  "Anti-EU / European Instability": "#f59e0b",
  "Ukraine Conflict Revisionism": "#8b5cf6",
  "Western Hypocrisy / Moral Equivalence": "#06b6d4",
  "Global South / Multipolar": "#10b981",
  "Health Disinformation": "#ec4899",
  "Election Interference": "#3b82f6",
  "Telegram Amplification": "#64748b",
};

const CONFIDENCE_STYLES: Record<string, { borderStyle: string; opacity: number }> = {
  high: { borderStyle: "solid", opacity: 1 },
  moderate: { borderStyle: "solid", opacity: 0.8 },
  low: { borderStyle: "dashed", opacity: 0.6 },
};

interface NarrativeTagsProps {
  matches: NarrativeMatchItem[];
  compact?: boolean;
}

export const NarrativeTags = ({ matches, compact = false }: NarrativeTagsProps) => {
  if (!matches || matches.length === 0) {
    return compact ? null : (
      <Box sx={{ py: 1 }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
          No known narrative patterns detected
        </Typography>
      </Box>
    );
  }

  if (compact) {
    return (
      <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5 }}>
        {matches.slice(0, 3).map((m) => {
          const color = CATEGORY_COLORS[m.category || ""] || "#64748b";
          return (
            <Tooltip key={m.id} title={`${m.narrative_name} (${m.confidence} confidence, ${m.match_count} keywords)`}>
              <Chip
                size="small"
                label={m.narrative_id}
                sx={{
                  fontSize: "0.6rem",
                  height: 18,
                  fontWeight: 700,
                  fontFamily: "monospace",
                  backgroundColor: `${color}20`,
                  color: color,
                  borderColor: color,
                  border: "1px solid",
                }}
              />
            </Tooltip>
          );
        })}
        {matches.length > 3 && (
          <Chip
            size="small"
            label={`+${matches.length - 3}`}
            sx={{ fontSize: "0.6rem", height: 18, opacity: 0.6 }}
            variant="outlined"
          />
        )}
      </Stack>
    );
  }

  return (
    <Box>
      <Typography variant="overline" color="text.secondary" fontWeight={700} sx={{ display: "block", mb: 1 }}>
        Detected Narratives ({matches.length})
      </Typography>
      <Stack spacing={1.5}>
        {matches.map((m) => {
          const color = CATEGORY_COLORS[m.category || ""] || "#64748b";
          const confStyle = CONFIDENCE_STYLES[m.confidence || "low"] || CONFIDENCE_STYLES.low;
          return (
            <Box
              key={m.id}
              sx={{
                p: 1.5,
                borderRadius: 2,
                backgroundColor: `${color}08`,
                borderLeft: `3px ${confStyle.borderStyle} ${color}`,
                opacity: confStyle.opacity,
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                <Box sx={{ flex: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip
                      size="small"
                      label={m.narrative_id}
                      sx={{
                        fontSize: "0.6rem",
                        height: 18,
                        fontWeight: 700,
                        fontFamily: "monospace",
                        backgroundColor: `${color}20`,
                        color: color,
                      }}
                    />
                    <Chip
                      size="small"
                      label={m.confidence}
                      variant="outlined"
                      sx={{
                        fontSize: "0.55rem",
                        height: 16,
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    />
                  </Stack>
                  <Typography variant="body2" fontWeight={600} sx={{ mt: 0.5 }}>
                    {m.narrative_name}
                  </Typography>
                  {m.category && (
                    <Typography variant="caption" color="text.secondary">
                      {m.category}
                    </Typography>
                  )}
                </Box>
                <Tooltip title={`${m.match_count} keyword matches: ${m.matched_keywords?.join(", ")}`}>
                  <Chip
                    size="small"
                    label={`${m.match_count} hits`}
                    sx={{
                      fontSize: "0.6rem",
                      height: 18,
                      fontWeight: 700,
                      backgroundColor: "rgba(148,163,184,0.1)",
                    }}
                  />
                </Tooltip>
              </Stack>
              {m.matched_keywords && m.matched_keywords.length > 0 && (
                <Stack direction="row" spacing={0.5} sx={{ mt: 1, flexWrap: "wrap", gap: 0.5 }}>
                  {m.matched_keywords.slice(0, 6).map((kw, i) => (
                    <Chip
                      key={i}
                      size="small"
                      label={kw}
                      variant="outlined"
                      sx={{
                        fontSize: "0.55rem",
                        height: 16,
                        borderColor: "rgba(148,163,184,0.2)",
                      }}
                    />
                  ))}
                  {m.matched_keywords.length > 6 && (
                    <Typography variant="caption" color="text.secondary" sx={{ alignSelf: "center" }}>
                      +{m.matched_keywords.length - 6} more
                    </Typography>
                  )}
                </Stack>
              )}
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
};
