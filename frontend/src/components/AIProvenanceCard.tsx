/**
 * AIProvenanceCard — EU AI Act Art. 50 compliance disclosure component.
 *
 * Renders a compact, tiered AI provenance indicator that:
 *  - Primary: shows a persistent "AI-Generated" badge with quality confidence tier
 *  - Secondary: expandable detail panel with model identity, prompt version,
 *    generation timestamp, quality score, and the full legal disclosure text
 *
 * Design principles (per EU Code of Practice on AI-Generated Content, Draft 2):
 *  - NOT dismissible — disclosure must be visible at first encounter
 *  - Tiered (badge → detail) to avoid transparency fatigue
 *  - Machine-readable via structured ai_metadata in the API response
 *  - Confidence tier colour-coded: ≥60=green, ≥40=amber, <40=red
 */
import { useState } from "react";
import {
  Box,
  Chip,
  Collapse,
  Divider,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import VerifiedUserIcon from "@mui/icons-material/VerifiedUser";
import type { AIMetadata } from "../api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getQualityColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return "#94a3b8";
  if (score >= 60) return "#10b981"; // excellent/good → green
  if (score >= 40) return "#f59e0b"; // acceptable → amber
  return "#ef4444";                  // poor/failing → red
}

function getQualityTier(score: number | null | undefined, rating: string | null | undefined): string {
  if (rating) return rating;
  if (score === null || score === undefined) return "Unscored";
  if (score >= 60) return "High Confidence";
  if (score >= 40) return "Moderate Confidence";
  return "Low Confidence";
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  aiMetadata: AIMetadata;
  /** "report" for outlet analysis, "topic" for topic mode runs */
  context?: "report" | "topic";
}

export function AIProvenanceCard({ aiMetadata, context = "report" }: Props) {
  const [expanded, setExpanded] = useState(false);
  const qualityColor = getQualityColor(aiMetadata.quality_score);
  const qualityTier = getQualityTier(aiMetadata.quality_score, aiMetadata.quality_rating);

  return (
    <Box
      sx={{
        border: "1px solid rgba(148,163,184,0.15)",
        borderRadius: 1.5,
        backgroundColor: "rgba(15,23,42,0.6)",
        overflow: "hidden",
      }}
      role="note"
      aria-label="AI provenance disclosure"
    >
      {/* ── Primary row: always visible ── */}
      <Box
        sx={{
          display: "flex", alignItems: "center", gap: 1, px: 1.5, py: 0.75,
          cursor: "pointer",
          "&:hover": { backgroundColor: "rgba(255,255,255,0.02)" },
        }}
        onClick={() => setExpanded((e) => !e)}
      >
        <SmartToyIcon sx={{ fontSize: 14, color: "#64748b", flexShrink: 0 }} />

        {/* AI-Generated label */}
        <Typography
          variant="caption"
          sx={{ fontSize: "0.68rem", color: "#64748b", fontWeight: 600, letterSpacing: "0.04em" }}
        >
          AI-GENERATED
        </Typography>

        <Typography variant="caption" sx={{ fontSize: "0.68rem", color: "#334155" }}>·</Typography>

        {/* Model badge */}
        <Chip
          label={aiMetadata.model_id}
          size="small"
          sx={{
            height: 16, fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.03em",
            backgroundColor: "rgba(99,102,241,0.12)", color: "#818cf8",
            border: "1px solid rgba(99,102,241,0.2)",
            "& .MuiChip-label": { px: 0.75 },
          }}
        />

        {/* Quality confidence badge — only when available */}
        {aiMetadata.quality_score !== null && aiMetadata.quality_score !== undefined && (
          <>
            <Typography variant="caption" sx={{ fontSize: "0.68rem", color: "#334155" }}>·</Typography>
            <Chip
              label={`${qualityTier} ${aiMetadata.quality_score}/70`}
              size="small"
              sx={{
                height: 16, fontSize: "0.6rem", fontWeight: 700,
                backgroundColor: `${qualityColor}14`, color: qualityColor,
                border: `1px solid ${qualityColor}30`,
                "& .MuiChip-label": { px: 0.75 },
              }}
            />
          </>
        )}

        {/* Human review required — always shown */}
        <Tooltip title="This AI output requires review by a qualified human analyst before operational use (EU AI Act Art. 50)" arrow>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.4, ml: "auto" }}>
            <VerifiedUserIcon sx={{ fontSize: 12, color: "#f59e0b" }} />
            <Typography
              variant="caption"
              sx={{ fontSize: "0.62rem", color: "#f59e0b", fontWeight: 700, letterSpacing: "0.03em" }}
            >
              REVIEW REQUIRED
            </Typography>
          </Box>
        </Tooltip>

        <IconButton size="small" sx={{ p: 0.2, ml: 0.5, color: "#475569" }}>
          {expanded ? <ExpandLessIcon sx={{ fontSize: 14 }} /> : <ExpandMoreIcon sx={{ fontSize: 14 }} />}
        </IconButton>
      </Box>

      {/* ── Secondary: expanded provenance detail ── */}
      <Collapse in={expanded}>
        <Divider sx={{ borderColor: "rgba(148,163,184,0.08)" }} />
        <Box sx={{ px: 1.5, py: 1.25, display: "flex", flexDirection: "column", gap: 1 }}>

          {/* Provenance fields */}
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.75 }}>
            <ProvenanceField label="Model" value={aiMetadata.model_id} />
            {aiMetadata.prompt_version && (
              <ProvenanceField label="Prompt version" value={aiMetadata.prompt_version} />
            )}
            <ProvenanceField label="Generated" value={formatTimestamp(aiMetadata.generated_at)} />
            {context === "report" && aiMetadata.quality_score !== null && aiMetadata.quality_score !== undefined && (
              <ProvenanceField
                label="Quality score"
                value={`${aiMetadata.quality_score}/70 — ${qualityTier}`}
                valueColor={qualityColor}
              />
            )}
          </Box>

          {/* Legal disclosure text */}
          <Box
            sx={{
              mt: 0.5, px: 1.25, py: 0.75,
              backgroundColor: "rgba(245,158,11,0.05)",
              border: "1px solid rgba(245,158,11,0.15)",
              borderRadius: 1,
            }}
          >
            <Typography variant="caption" sx={{ fontSize: "0.7rem", color: "#94a3b8", lineHeight: 1.5 }}>
              {aiMetadata.disclosure}
            </Typography>
          </Box>

          {/* EU AI Act reference */}
          <Typography variant="caption" sx={{ fontSize: "0.62rem", color: "#334155" }}>
            Disclosure in compliance with EU AI Act Art. 50 — Transparency obligations for AI-generated content.
          </Typography>
        </Box>
      </Collapse>
    </Box>
  );
}

// ---------------------------------------------------------------------------
// Helper sub-component
// ---------------------------------------------------------------------------

function ProvenanceField({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <Box>
      <Typography variant="caption" sx={{ fontSize: "0.6rem", color: "#475569", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}>
        {label}
      </Typography>
      <Typography variant="caption" sx={{ fontSize: "0.72rem", color: valueColor ?? "#94a3b8", display: "block" }}>
        {value}
      </Typography>
    </Box>
  );
}
