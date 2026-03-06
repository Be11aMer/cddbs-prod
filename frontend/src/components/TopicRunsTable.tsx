import {
  Box,
  Chip,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Tooltip,
  LinearProgress,
  TextField,
  InputAdornment,
  Pagination,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import VisibilityIcon from "@mui/icons-material/Visibility";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import type { TopicRunStatus } from "../api";
import { useState, useMemo } from "react";

const ROWS_PER_PAGE = 20;

interface Props {
  runs: TopicRunStatus[];
  onRefresh: () => void;
  onOpenDetail: (id: number) => void;
  isLoading?: boolean;
}

const statusColor: Record<string, "default" | "primary" | "success" | "error" | "warning"> = {
  pending: "default",
  running: "primary",
  completed: "success",
  failed: "error",
};

function StatusChip({ status }: { status: string }) {
  return (
    <Chip
      label={status.toUpperCase()}
      color={statusColor[status] ?? "default"}
      size="small"
      sx={
        status === "running"
          ? { animation: "pulse-glow 2s cubic-bezier(0.4,0,0.6,1) infinite" }
          : status === "completed"
          ? { boxShadow: "0 0 8px rgba(16,185,129,0.3)" }
          : {}
      }
    />
  );
}

export const TopicRunsTable = ({ runs, onRefresh, onOpenDetail, isLoading }: Props) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return runs;
    const q = searchQuery.toLowerCase();
    return runs.filter((r) => r.topic.toLowerCase().includes(q) || r.status.toLowerCase().includes(q));
  }, [runs, searchQuery]);

  const totalPages = Math.ceil(filtered.length / ROWS_PER_PAGE);
  const paginated = filtered.slice((page - 1) * ROWS_PER_PAGE, page * ROWS_PER_PAGE);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", gap: 2 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <Box
          sx={{
            width: 36, height: 36, borderRadius: 2,
            backgroundColor: "rgba(139,92,246,0.1)",
            border: "1px solid rgba(139,92,246,0.2)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}
        >
          <TravelExploreIcon sx={{ fontSize: 20, color: "#8b5cf6" }} />
        </Box>
        <Box>
          <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.2 }}>
            Topic Analysis
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Discover which outlets use a topic to push narratives
          </Typography>
        </Box>
        <Tooltip title="Refresh">
          <IconButton onClick={onRefresh} size="small" sx={{ ml: "auto" }}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Search */}
      <Box sx={{ display: "flex", gap: 1.5 }}>
        <TextField
          size="small"
          placeholder="Search topics..."
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
          sx={{ flexGrow: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: "text.disabled" }} />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Table */}
      <TableContainer
        component={Paper}
        sx={{
          flexGrow: 1,
          overflow: "auto",
          backgroundColor: "rgba(12,20,56,0.4)",
          backdropFilter: "blur(10px)",
          border: "1px solid rgba(148,163,184,0.1)",
          borderRadius: 2,
        }}
      >
        {isLoading && <LinearProgress sx={{ position: "absolute", top: 0, left: 0, right: 0 }} />}
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>ID</TableCell>
              <TableCell>Topic</TableCell>
              <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>Time Period</TableCell>
              <TableCell>Outlets Found</TableCell>
              <TableCell>Status</TableCell>
              <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>Created</TableCell>
              <TableCell align="right">Results</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginated.length === 0 && !isLoading && (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                  <TravelExploreIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1, display: "block", mx: "auto" }} />
                  <Typography color="text.secondary">
                    {searchQuery ? "No matching topic runs." : "No topic analyses yet. Start one with New Analysis → Topic Mode."}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {paginated.map((run) => (
              <TableRow
                key={run.id}
                hover
                sx={{
                  cursor: run.status === "completed" ? "pointer" : "default",
                  "&:last-child td": { borderBottom: 0 },
                }}
                onClick={() => run.status === "completed" && onOpenDetail(run.id)}
              >
                <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>
                  <Typography variant="body2" color="text.disabled">#{run.id}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight={600} sx={{
                    maxWidth: { xs: 160, sm: 280, md: 400 },
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>
                    {run.topic}
                  </Typography>
                </TableCell>
                <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>
                  <Typography variant="body2" color="text.secondary" sx={{ textTransform: "uppercase", fontSize: "0.7rem" }}>
                    {({ h: "Hour", d: "Day", w: "Week", m: "Month", y: "Year" } as Record<string, string>)[run.date_filter] ?? run.date_filter}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight={700} sx={{ color: run.outlets_found > 0 ? "#8b5cf6" : "text.secondary" }}>
                    {run.outlets_found}
                  </Typography>
                </TableCell>
                <TableCell>
                  <StatusChip status={run.status} />
                  {run.error && (
                    <Tooltip title={run.error}>
                      <Typography variant="caption" color="error" sx={{ display: "block", mt: 0.25, fontSize: "0.62rem" }}>
                        Error
                      </Typography>
                    </Tooltip>
                  )}
                </TableCell>
                <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>
                  <Typography variant="body2" color="text.secondary">
                    {new Date(run.created_at).toLocaleString()}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title={run.status === "completed" ? "View results" : "Results available after completion"}>
                    <span>
                      <IconButton
                        size="small"
                        disabled={run.status !== "completed"}
                        onClick={(e) => { e.stopPropagation(); onOpenDetail(run.id); }}
                      >
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalPages > 1 && (
        <Box sx={{ display: "flex", justifyContent: "center" }}>
          <Pagination count={totalPages} page={page} onChange={(_, v) => setPage(v)} size="small" />
        </Box>
      )}
    </Box>
  );
};
