import {
  Box,
  Typography,
  Chip,
  Stack,
  Link as MuiLink,
  LinearProgress,
  Tooltip,
  Collapse,
  IconButton,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import SentimentSatisfiedIcon from "@mui/icons-material/SentimentSatisfied";
import SentimentNeutralIcon from "@mui/icons-material/SentimentNeutral";
import SentimentDissatisfiedIcon from "@mui/icons-material/SentimentDissatisfied";
import { useState } from "react";
import type { ArticleSummary } from "../api";

const PropagandaGauge = ({ score }: { score: number }) => {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? "#ef4444" : pct >= 40 ? "#f59e0b" : "#10b981";
  const label =
    pct >= 70 ? "HIGH" : pct >= 40 ? "MODERATE" : "LOW";

  return (
    <Box sx={{ width: 100 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
        <Typography variant="caption" sx={{ fontSize: "0.6rem", color: "text.secondary" }}>
          PROP. SCORE
        </Typography>
        <Typography variant="caption" sx={{ fontSize: "0.65rem", fontWeight: 800, color }}>
          {pct}%
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{
          height: 4,
          borderRadius: 2,
          backgroundColor: "rgba(255,255,255,0.06)",
          "& .MuiLinearProgress-bar": { backgroundColor: color, borderRadius: 2 },
        }}
      />
      <Typography
        variant="caption"
        sx={{ fontSize: "0.55rem", fontWeight: 700, color, mt: 0.25, display: "block", textAlign: "right" }}
      >
        {label}
      </Typography>
    </Box>
  );
};

const SentimentIcon = ({ sentiment }: { sentiment: string }) => {
  const s = (sentiment || "").toLowerCase();
  if (s === "positive")
    return (
      <Tooltip title="Positive sentiment">
        <SentimentSatisfiedIcon sx={{ fontSize: 16, color: "#10b981" }} />
      </Tooltip>
    );
  if (s === "negative")
    return (
      <Tooltip title="Negative sentiment">
        <SentimentDissatisfiedIcon sx={{ fontSize: 16, color: "#ef4444" }} />
      </Tooltip>
    );
  return (
    <Tooltip title="Neutral sentiment">
      <SentimentNeutralIcon sx={{ fontSize: 16, color: "#94a3b8" }} />
    </Tooltip>
  );
};

const ArticleCard = ({ article }: { article: ArticleSummary }) => {
  const [expanded, setExpanded] = useState(false);
  const a = article.analysis;
  const hasAnalysis = !!a;

  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 2,
        border: "1px solid rgba(148,163,184,0.1)",
        backgroundColor: "rgba(148, 163, 184, 0.02)",
        transition: "border-color 0.2s",
        "&:hover": { borderColor: "rgba(148,163,184,0.2)" },
      }}
    >
      {/* Header row */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" fontWeight={700} sx={{ lineHeight: 1.3, mb: 0.5 }}>
            {article.title}
          </Typography>
          {article.link && (
            <MuiLink
              href={article.link}
              target="_blank"
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mb: 0.5, wordBreak: "break-all" }}
            >
              {(() => {
                try {
                  return new URL(article.link).hostname;
                } catch {
                  return article.link;
                }
              })()}
            </MuiLink>
          )}
          {article.date && (
            <Typography variant="caption" color="text.disabled" sx={{ fontSize: "0.65rem" }}>
              {article.date}
            </Typography>
          )}
        </Box>

        {/* Propaganda gauge + sentiment */}
        {hasAnalysis && (
          <Stack alignItems="center" spacing={0.5} sx={{ flexShrink: 0 }}>
            {a.propaganda_score != null && <PropagandaGauge score={a.propaganda_score} />}
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {a.sentiment && <SentimentIcon sentiment={a.sentiment} />}
              {a.sentiment && (
                <Typography variant="caption" sx={{ fontSize: "0.65rem", color: "text.secondary", textTransform: "capitalize" }}>
                  {a.sentiment}
                </Typography>
              )}
            </Box>
          </Stack>
        )}
      </Box>

      {/* Framing summary */}
      {hasAnalysis && a.framing && (
        <Typography
          variant="body2"
          sx={{
            mt: 1,
            p: 1,
            borderRadius: 1,
            backgroundColor: "rgba(59, 130, 246, 0.04)",
            borderLeft: "3px solid rgba(59, 130, 246, 0.3)",
            fontSize: "0.85rem",
            lineHeight: 1.5,
            color: "text.secondary",
          }}
        >
          {a.framing}
        </Typography>
      )}

      {/* Narrative themes + claims chips */}
      {hasAnalysis && (a.narrative_themes?.length || a.key_actors?.length) && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
          {a.narrative_themes?.map((theme, i) => (
            <Chip
              key={`t-${i}`}
              label={theme}
              size="small"
              sx={{
                height: 18,
                fontSize: "0.6rem",
                fontWeight: 700,
                backgroundColor: "rgba(245,158,11,0.1)",
                color: "#f59e0b",
                border: "1px solid rgba(245,158,11,0.2)",
                "& .MuiChip-label": { px: 0.75 },
              }}
            />
          ))}
          {a.key_actors?.map((actor, i) => (
            <Chip
              key={`a-${i}`}
              label={actor}
              size="small"
              sx={{
                height: 18,
                fontSize: "0.6rem",
                backgroundColor: "rgba(59,130,246,0.08)",
                color: "#64748b",
                "& .MuiChip-label": { px: 0.75 },
              }}
            />
          ))}
        </Box>
      )}

      {/* Expandable details */}
      {hasAnalysis && (a.key_claims?.length || a.unverified_statements?.length || a.analysis_notes) && (
        <>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              mt: 1,
              cursor: "pointer",
              "&:hover": { "& .expand-label": { color: "primary.light" } },
            }}
            onClick={() => setExpanded(!expanded)}
          >
            <Typography
              className="expand-label"
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: "0.7rem", transition: "color 0.15s" }}
            >
              {expanded ? "Hide details" : "Show analyst notes & claims"}
            </Typography>
            <IconButton size="small" sx={{ ml: 0.5, p: 0 }}>
              {expanded ? (
                <ExpandLessIcon sx={{ fontSize: 14, color: "text.secondary" }} />
              ) : (
                <ExpandMoreIcon sx={{ fontSize: 14, color: "text.secondary" }} />
              )}
            </IconButton>
          </Box>

          <Collapse in={expanded}>
            <Stack spacing={1} sx={{ mt: 1 }}>
              {/* Key Claims */}
              {a.key_claims && a.key_claims.length > 0 && (
                <Box>
                  <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ fontSize: "0.65rem", textTransform: "uppercase", mb: 0.5, display: "block" }}>
                    Key Claims
                  </Typography>
                  {a.key_claims.map((claim, i) => (
                    <Typography key={i} variant="caption" display="block" sx={{ pl: 1, mb: 0.25, fontSize: "0.8rem", lineHeight: 1.4, borderLeft: "2px solid rgba(148,163,184,0.15)" }}>
                      {claim}
                    </Typography>
                  ))}
                </Box>
              )}

              {/* Unverified Statements */}
              {a.unverified_statements && a.unverified_statements.length > 0 && (
                <Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
                    <WarningAmberIcon sx={{ fontSize: 12, color: "#f59e0b" }} />
                    <Typography variant="caption" fontWeight={700} sx={{ fontSize: "0.65rem", textTransform: "uppercase", color: "#f59e0b" }}>
                      Unverified
                    </Typography>
                  </Box>
                  {a.unverified_statements.map((stmt, i) => (
                    <Typography key={i} variant="caption" display="block" sx={{ pl: 1, mb: 0.25, fontSize: "0.8rem", lineHeight: 1.4, color: "text.secondary", borderLeft: "2px solid rgba(245,158,11,0.3)" }}>
                      {stmt}
                    </Typography>
                  ))}
                </Box>
              )}

              {/* Analysis Notes */}
              {a.analysis_notes && (
                <Box>
                  <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ fontSize: "0.65rem", textTransform: "uppercase", mb: 0.5, display: "block" }}>
                    Analyst Notes
                  </Typography>
                  <Typography variant="caption" sx={{ fontSize: "0.8rem", lineHeight: 1.5, color: "text.secondary" }}>
                    {a.analysis_notes}
                  </Typography>
                </Box>
              )}
            </Stack>
          </Collapse>
        </>
      )}
    </Box>
  );
};

interface Props {
  articles: ArticleSummary[];
}

export const AnnotatedArticleCards = ({ articles }: Props) => {
  if (!articles?.length) return null;

  const hasAnyAnalysis = articles.some((a) => a.analysis);
  if (!hasAnyAnalysis) return null;

  return (
    <Stack spacing={1.5}>
      {articles.map((article) => (
        <ArticleCard key={article.id} article={article} />
      ))}
    </Stack>
  );
};
