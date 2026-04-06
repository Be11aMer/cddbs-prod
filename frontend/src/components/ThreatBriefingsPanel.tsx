import {
  Box,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Divider,
  Badge,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import ArticleIcon from "@mui/icons-material/Article";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchThreatBriefings,
  triggerQuarterlyReport,
  type ThreatBriefingItem,
} from "../api";
import { ThreatBriefingDetail } from "./ThreatBriefingDetail";

const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  moderate: "#f59e0b",
  low: "#10b981",
};

const TYPE_LABELS: Record<string, string> = {
  sitrep: "SitRep",
  daily_digest: "Daily Digest",
  quarterly_report: "Quarterly Report",
};

const TYPE_COLORS: Record<string, string> = {
  sitrep: "#3b82f6",
  daily_digest: "#10b981",
  quarterly_report: "#8b5cf6",
};

function getRiskFromJson(item: ThreatBriefingItem): string | null {
  return null; // risk level only available in full detail, shown in list as type badge
}

function BriefingCard({
  item,
  onClick,
}: {
  item: ThreatBriefingItem;
  onClick: () => void;
}) {
  const typeColor = TYPE_COLORS[item.briefing_type] || "#94a3b8";
  const typeLabel = TYPE_LABELS[item.briefing_type] || item.briefing_type;
  const createdAt = item.created_at ? new Date(item.created_at) : null;
  const isGenerating = item.title?.includes("generating...");

  return (
    <Box
      onClick={!isGenerating ? onClick : undefined}
      sx={{
        p: 1.75,
        borderRadius: 2,
        border: "1px solid rgba(148,163,184,0.1)",
        backgroundColor: "rgba(255,255,255,0.02)",
        cursor: isGenerating ? "default" : "pointer",
        transition: "all 0.15s ease",
        "&:hover": isGenerating ? {} : {
          backgroundColor: "rgba(255,255,255,0.04)",
          borderColor: `${typeColor}44`,
        },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 0.75 }}>
        <Chip
          size="small"
          label={typeLabel}
          sx={{
            fontSize: "0.6rem", fontWeight: 700, height: 18,
            backgroundColor: `${typeColor}22`, color: typeColor,
          }}
        />
        {item.has_framing_analysis && (
          <Tooltip title="Includes cross-source framing analysis">
            <CompareArrowsIcon sx={{ fontSize: 14, color: "#8b5cf6", mt: 0.25 }} />
          </Tooltip>
        )}
        {isGenerating && <CircularProgress size={12} sx={{ ml: "auto", mt: 0.25 }} />}
        {!isGenerating && (
          <Typography variant="caption" sx={{ color: "text.secondary", ml: "auto", whiteSpace: "nowrap" }}>
            {createdAt ? createdAt.toLocaleDateString() : ""}
          </Typography>
        )}
      </Box>

      <Typography
        variant="body2"
        fontWeight={600}
        sx={{ fontSize: "0.8rem", lineHeight: 1.35, mb: 0.5, color: isGenerating ? "text.secondary" : "text.primary" }}
      >
        {item.title || "Untitled Briefing"}
      </Typography>

      {item.executive_summary && (
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            lineHeight: 1.5,
          }}
        >
          {item.executive_summary}
        </Typography>
      )}

      <Box sx={{ display: "flex", gap: 1, mt: 0.75, flexWrap: "wrap" }}>
        {item.articles_analyzed > 0 && (
          <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.65rem" }}>
            {item.articles_analyzed} articles · {item.sources_compared} sources
          </Typography>
        )}
        {item.period_start && item.briefing_type !== "sitrep" && (
          <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.65rem" }}>
            {new Date(item.period_start).toLocaleDateString()} – {item.period_end ? new Date(item.period_end).toLocaleDateString() : "now"}
          </Typography>
        )}
      </Box>
    </Box>
  );
}


function QuarterlyReportDialog({
  open,
  onClose,
  onGenerate,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  onGenerate: (year: number, quarter: number) => void;
  isLoading: boolean;
}) {
  const currentYear = new Date().getFullYear();
  const currentQuarter = Math.ceil((new Date().getMonth() + 1) / 3);
  const [year, setYear] = useState(currentYear);
  const [quarter, setQuarter] = useState(currentQuarter);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth
      PaperProps={{ sx: { backgroundColor: "#0f172a", backgroundImage: "none", border: "1px solid rgba(148,163,184,0.1)" } }}
    >
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CalendarTodayIcon sx={{ fontSize: 18, color: "#8b5cf6" }} />
          <Typography fontWeight={700}>Generate Quarterly Report</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 2, fontSize: "0.8rem" }}>
          Compiles all SitReps and daily digests from the selected quarter into a publishable threat assessment.
        </Typography>
        <Stack direction="row" spacing={2}>
          <TextField
            label="Year"
            type="number"
            size="small"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            inputProps={{ min: 2024, max: 2030 }}
            fullWidth
          />
          <FormControl size="small" fullWidth>
            <InputLabel>Quarter</InputLabel>
            <Select value={quarter} label="Quarter" onChange={(e) => setQuarter(Number(e.target.value))}>
              <MenuItem value={1}>Q1 (Jan–Mar)</MenuItem>
              <MenuItem value={2}>Q2 (Apr–Jun)</MenuItem>
              <MenuItem value={3}>Q3 (Jul–Sep)</MenuItem>
              <MenuItem value={4}>Q4 (Oct–Dec)</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} sx={{ color: "text.secondary" }}>Cancel</Button>
        <Button
          variant="contained"
          onClick={() => onGenerate(year, quarter)}
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={14} color="inherit" /> : <AutoAwesomeIcon />}
        >
          Generate Q{quarter} {year}
        </Button>
      </DialogActions>
    </Dialog>
  );
}


export function ThreatBriefingsPanel() {
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [quarterlyDialogOpen, setQuarterlyDialogOpen] = useState(false);

  const { data: briefings, isLoading, refetch } = useQuery({
    queryKey: ["threat-briefings", typeFilter],
    queryFn: () => fetchThreatBriefings({ briefing_type: typeFilter || undefined, limit: 50 }),
    refetchInterval: 30000,
  });

  const quarterlyMutation = useMutation({
    mutationFn: ({ year, quarter }: { year: number; quarter: number }) =>
      triggerQuarterlyReport(year, quarter),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["threat-briefings"] });
      setQuarterlyDialogOpen(false);
    },
  });

  const sitreps = briefings?.filter((b) => b.briefing_type === "sitrep") ?? [];
  const digests = briefings?.filter((b) => b.briefing_type === "daily_digest") ?? [];
  const quarterlies = briefings?.filter((b) => b.briefing_type === "quarterly_report") ?? [];

  const totalCount = briefings?.length ?? 0;

  function openDetail(id: number) {
    setSelectedId(id);
    setDetailOpen(true);
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2.5 }}>
        <ArticleIcon sx={{ color: "primary.main", fontSize: 20 }} />
        <Typography variant="h6" fontWeight={800} sx={{ fontSize: "1rem" }}>
          Threat Briefings
        </Typography>
        {totalCount > 0 && (
          <Badge badgeContent={totalCount} color="primary" sx={{ ml: 0.5 }}>
            <Box sx={{ width: 8 }} />
          </Badge>
        )}
        <Box sx={{ ml: "auto", display: "flex", gap: 1, alignItems: "center" }}>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel sx={{ fontSize: "0.75rem" }}>Filter by type</InputLabel>
            <Select
              value={typeFilter}
              label="Filter by type"
              onChange={(e) => setTypeFilter(e.target.value)}
              sx={{ fontSize: "0.75rem" }}
            >
              <MenuItem value="">All types</MenuItem>
              <MenuItem value="sitrep">SitReps</MenuItem>
              <MenuItem value="daily_digest">Daily Digests</MenuItem>
              <MenuItem value="quarterly_report">Quarterly Reports</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={() => refetch()} sx={{ color: "text.secondary" }}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Generate Quarterly Report">
            <Button
              size="small"
              variant="outlined"
              startIcon={<CalendarTodayIcon fontSize="small" />}
              onClick={() => setQuarterlyDialogOpen(true)}
              sx={{ fontSize: "0.72rem", borderColor: "#8b5cf6", color: "#8b5cf6", "&:hover": { borderColor: "#7c3aed", backgroundColor: "#7c3aed11" } }}
            >
              Quarterly Report
            </Button>
          </Tooltip>
        </Box>
      </Box>

      {isLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress size={28} />
        </Box>
      )}

      {!isLoading && totalCount === 0 && (
        <Alert severity="info" sx={{ backgroundColor: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)" }}>
          No threat briefings generated yet. Briefings are auto-generated when high-risk event clusters are detected (every 12 hours by default).
        </Alert>
      )}

      {/* SitReps */}
      {(!typeFilter || typeFilter === "sitrep") && sitreps.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="overline" sx={{ color: "#3b82f6", fontWeight: 800, fontSize: "0.65rem", letterSpacing: "0.1em", display: "block", mb: 1.5 }}>
            Situational Reports ({sitreps.length})
          </Typography>
          <Stack spacing={1}>
            {sitreps.map((b) => (
              <BriefingCard key={b.id} item={b} onClick={() => openDetail(b.id)} />
            ))}
          </Stack>
        </Box>
      )}

      {/* Daily Digests */}
      {(!typeFilter || typeFilter === "daily_digest") && digests.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Divider sx={{ mb: 2, opacity: 0.08 }} />
          <Typography variant="overline" sx={{ color: "#10b981", fontWeight: 800, fontSize: "0.65rem", letterSpacing: "0.1em", display: "block", mb: 1.5 }}>
            Daily Digests ({digests.length})
          </Typography>
          <Stack spacing={1}>
            {digests.map((b) => (
              <BriefingCard key={b.id} item={b} onClick={() => openDetail(b.id)} />
            ))}
          </Stack>
        </Box>
      )}

      {/* Quarterly Reports */}
      {(!typeFilter || typeFilter === "quarterly_report") && quarterlies.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Divider sx={{ mb: 2, opacity: 0.08 }} />
          <Typography variant="overline" sx={{ color: "#8b5cf6", fontWeight: 800, fontSize: "0.65rem", letterSpacing: "0.1em", display: "block", mb: 1.5 }}>
            Quarterly Reports ({quarterlies.length})
          </Typography>
          <Stack spacing={1}>
            {quarterlies.map((b) => (
              <BriefingCard key={b.id} item={b} onClick={() => openDetail(b.id)} />
            ))}
          </Stack>
        </Box>
      )}

      {/* Detail dialog */}
      <ThreatBriefingDetail
        briefingId={selectedId}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      />

      {/* Quarterly report generator dialog */}
      <QuarterlyReportDialog
        open={quarterlyDialogOpen}
        onClose={() => setQuarterlyDialogOpen(false)}
        onGenerate={(year, quarter) => quarterlyMutation.mutate({ year, quarter })}
        isLoading={quarterlyMutation.isPending}
      />
    </Box>
  );
}
