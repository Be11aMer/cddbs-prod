import { Box, Chip, Tooltip, Typography, Stack } from "@mui/material";
import type { QualityResponse } from "../api";

const ratingConfig: Record<
  string,
  { color: "success" | "info" | "warning" | "error" | "default"; label: string; bgColor: string }
> = {
  Excellent: { color: "success", label: "Excellent", bgColor: "rgba(16, 185, 129, 0.15)" },
  Good: { color: "info", label: "Good", bgColor: "rgba(59, 130, 246, 0.15)" },
  Acceptable: { color: "warning", label: "Acceptable", bgColor: "rgba(245, 158, 11, 0.15)" },
  Poor: { color: "error", label: "Poor", bgColor: "rgba(239, 68, 68, 0.15)" },
  Failing: { color: "error", label: "Failing", bgColor: "rgba(239, 68, 68, 0.25)" },
};

interface QualityBadgeProps {
  quality: QualityResponse | null | undefined;
  compact?: boolean;
}

export const QualityBadge = ({ quality, compact = false }: QualityBadgeProps) => {
  if (!quality || quality.total_score === null) {
    return compact ? null : (
      <Chip
        size="small"
        label="No Score"
        variant="outlined"
        sx={{ fontSize: "0.65rem", height: 20, opacity: 0.5 }}
      />
    );
  }

  const rating = quality.rating || "Failing";
  const config = ratingConfig[rating] || ratingConfig.Failing;
  const percentage = Math.round((quality.total_score / quality.max_score) * 100);

  if (compact) {
    return (
      <Tooltip
        title={
          <Box sx={{ p: 0.5 }}>
            <Typography variant="caption" fontWeight={700}>
              Quality: {quality.total_score}/{quality.max_score} ({rating})
            </Typography>
          </Box>
        }
      >
        <Chip
          size="small"
          label={`${quality.total_score}/${quality.max_score}`}
          color={config.color}
          variant="outlined"
          sx={{
            fontSize: "0.65rem",
            height: 20,
            fontWeight: 700,
          }}
        />
      </Tooltip>
    );
  }

  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 3,
        backgroundColor: config.bgColor,
        border: `1px solid`,
        borderColor: `${config.color}.main`,
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="overline" color="text.secondary" fontWeight={700} sx={{ display: "block", lineHeight: 1.2 }}>
            Quality Score
          </Typography>
          <Stack direction="row" alignItems="baseline" spacing={0.5} sx={{ mt: 0.5 }}>
            <Typography variant="h4" fontWeight={800}>
              {quality.total_score}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              / {quality.max_score}
            </Typography>
          </Stack>
        </Box>
        <Box sx={{ textAlign: "right" }}>
          <Chip
            label={rating}
            color={config.color}
            size="small"
            sx={{ fontWeight: 700, fontSize: "0.75rem" }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
            {percentage}%
          </Typography>
        </Box>
      </Stack>

      {/* Score bar */}
      <Box sx={{ mt: 1.5, height: 6, borderRadius: 3, backgroundColor: "rgba(148,163,184,0.1)", overflow: "hidden" }}>
        <Box
          sx={{
            height: "100%",
            width: `${percentage}%`,
            borderRadius: 3,
            backgroundColor: `${config.color}.main`,
            transition: "width 0.6s ease-out",
          }}
        />
      </Box>
    </Box>
  );
};
