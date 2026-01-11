import {
  Box,
  Chip,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  Typography,
  Tooltip,
  LinearProgress,
  TextField,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import VisibilityIcon from "@mui/icons-material/Visibility";
import type { RunStatus } from "../api";
import { useAppDispatch, useAppSelector } from "../hooks";
import { setSelectedRunId } from "../slices/runsSlice";
import { useState, useMemo } from "react";
import { TableSkeleton } from "./Skeletons";

interface Props {
  runs: RunStatus[];
  onRefresh: () => void;
  onOpenReport?: (id: number) => void;
  isLoading?: boolean;
}

const statusColor: Record<string, "default" | "primary" | "success" | "error"> =
{
  queued: "default",
  running: "primary",
  completed: "success",
  failed: "error",
};

const getStatusLabel = (status: string, message?: string | null): string => {
  switch (status) {
    case "queued":
      return "Queued - Waiting to start";
    case "running":
      return message || "Running - Fetching and analyzing articles";
    case "completed":
      return "Completed - Ready to view";
    case "failed":
      return message ? `Failed: ${message}` : "Failed - Check details";
    default:
      return status;
  }
};

const getStatusStyles = (status: string) => {
  switch (status) {
    case "running":
      return {
        animation: "pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      };
    case "completed":
      return {
        boxShadow: "0 0 10px rgba(16, 185, 129, 0.3)",
      };
    case "failed":
      return {
        boxShadow: "0 0 10px rgba(239, 68, 68, 0.4)",
      };
    case "queued":
      return {
        animation: "pulse-opacity 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      };
    default:
      return {};
  }
};

export const RunsTable = ({ runs, onRefresh, onOpenReport, isLoading }: Props) => {
  const dispatch = useAppDispatch();
  const selectedRunId = useAppSelector((s) => s.runs.selectedRunId);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dateFilter, setDateFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"id" | "outlet" | "country" | "created_at">("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Filter runs based on search and filters
  const filteredRuns = useMemo(() => {
    let filtered = [...runs]; // Create a copy to avoid mutating the original array

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (run) =>
          run.outlet.toLowerCase().includes(query) ||
          run.country?.toLowerCase().includes(query) ||
          run.id.toString().includes(query)
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter((run) => run.status === statusFilter);
    }

    // Date filter
    if (dateFilter !== "all") {
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
      const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

      filtered = filtered.filter((run) => {
        const runDate = new Date(run.created_at);
        switch (dateFilter) {
          case "today":
            return runDate >= today;
          case "week":
            return runDate >= weekAgo;
          case "month":
            return runDate >= monthAgo;
          default:
            return true;
        }
      });
    }

    // Sort
    filtered.sort((a, b) => {
      let aValue: any = a[sortBy];
      let bValue: any = b[sortBy];

      if (sortBy === "created_at") {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      } else if (typeof aValue === "string") {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }

      if (aValue < bValue) return sortOrder === "asc" ? -1 : 1;
      if (aValue > bValue) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [runs, searchQuery, statusFilter, dateFilter, sortBy, sortOrder]);

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
  };

  if (isLoading) {
    return <TableSkeleton />;
  }

  return (
    <Paper
      sx={{
        p: 2,
        border: "1px solid rgba(148,163,184,0.35)",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mb: 2,
        }}
      >
        <Typography variant="h6" fontWeight={600}>
          Analysis Runs
        </Typography>
        <Tooltip title="Refresh">
          <IconButton size="small" onClick={onRefresh}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Search and Filters */}
      <Box sx={{ mb: 2, display: "flex", gap: 1.5, flexWrap: "wrap" }}>
        <TextField
          size="small"
          placeholder="Search... (Ctrl+K)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ flexGrow: 1, minWidth: 200 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" color="action" />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <Box
                  sx={{
                    px: 0.8,
                    py: 0.2,
                    borderRadius: 1,
                    backgroundColor: "rgba(148, 163, 184, 0.1)",
                    border: "1px solid rgba(148, 163, 184, 0.2)",
                    fontSize: "0.65rem",
                    fontWeight: 700,
                    color: "text.secondary",
                    display: { xs: "none", sm: "block" },
                    mr: -0.5,
                  }}
                >
                  {navigator.platform.includes("Mac") ? "⌘K" : "Ctrl+K"}
                </Box>
              </InputAdornment>
            ),
          }}
        />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="all">All Statuses</MenuItem>
            <MenuItem value="running">Running</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
            <MenuItem value="queued">Queued</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Date</InputLabel>
          <Select
            value={dateFilter}
            label="Date"
            onChange={(e) => setDateFilter(e.target.value)}
          >
            <MenuItem value="all">All Time</MenuItem>
            <MenuItem value="today">Today</MenuItem>
            <MenuItem value="week">This Week</MenuItem>
            <MenuItem value="month">This Month</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <TableContainer sx={{ flexGrow: 1 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell
                onClick={() => handleSort("id")}
                sx={{ cursor: "pointer", userSelect: "none", "&:hover": { backgroundColor: "rgba(148, 163, 184, 0.1)" } }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  ID
                  {sortBy === "id" && (
                    sortOrder === "asc" ? <ArrowUpwardIcon sx={{ fontSize: 16 }} /> : <ArrowDownwardIcon sx={{ fontSize: 16 }} />
                  )}
                </Box>
              </TableCell>
              <TableCell
                onClick={() => handleSort("outlet")}
                sx={{ cursor: "pointer", userSelect: "none", "&:hover": { backgroundColor: "rgba(148, 163, 184, 0.1)" } }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  Outlet
                  {sortBy === "outlet" && (
                    sortOrder === "asc" ? <ArrowUpwardIcon sx={{ fontSize: 16 }} /> : <ArrowDownwardIcon sx={{ fontSize: 16 }} />
                  )}
                </Box>
              </TableCell>
              <TableCell
                onClick={() => handleSort("country")}
                sx={{ cursor: "pointer", userSelect: "none", "&:hover": { backgroundColor: "rgba(148, 163, 184, 0.1)" } }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  Country
                  {sortBy === "country" && (
                    sortOrder === "asc" ? <ArrowUpwardIcon sx={{ fontSize: 16 }} /> : <ArrowDownwardIcon sx={{ fontSize: 16 }} />
                  )}
                </Box>
              </TableCell>
              <TableCell
                onClick={() => handleSort("created_at")}
                sx={{ cursor: "pointer", userSelect: "none", "&:hover": { backgroundColor: "rgba(148, 163, 184, 0.1)" } }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  Created
                  {sortBy === "created_at" && (
                    sortOrder === "asc" ? <ArrowUpwardIcon sx={{ fontSize: 16 }} /> : <ArrowDownwardIcon sx={{ fontSize: 16 }} />
                  )}
                </Box>
              </TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Details</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredRuns.map((run) => (
              <TableRow
                key={run.id}
                hover
                sx={{
                  cursor: "pointer",
                  transition: "all 0.2s ease-in-out",
                  backgroundColor: selectedRunId === run.id ? "rgba(59, 130, 246, 0.08)" : "transparent",
                  borderLeft: selectedRunId === run.id ? "4px solid #3b82f6" : "0px solid transparent",
                  "&:hover": {
                    transform: "translateX(4px)",
                    boxShadow: selectedRunId === run.id
                      ? "none"
                      : "inset 3px 0 0 #3b82f6",
                  },
                }}
                onClick={() => dispatch(setSelectedRunId(run.id))}
              >
                <TableCell>{run.id}</TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight={500}>
                    {run.outlet}
                  </Typography>
                </TableCell>
                <TableCell>{run.country}</TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {new Date(run.created_at).toLocaleString()}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box>
                    <Tooltip title={getStatusLabel(run.status, run.message)}>
                      <Chip
                        size="small"
                        label={run.status}
                        color={statusColor[run.status] ?? "default"}
                        variant="outlined"
                        sx={{
                          ...getStatusStyles(run.status),
                          fontWeight: 600,
                          textTransform: "capitalize",
                        }}
                      />
                    </Tooltip>
                    {run.status === "running" && (
                      <Box sx={{ mt: 0.5 }}>
                        <LinearProgress
                          sx={{ height: 2, borderRadius: 1 }}
                        />
                      </Box>
                    )}
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="View Detailed Briefing">
                    <IconButton
                      size="small"
                      color="primary"
                      disabled={run.status !== "completed" && run.status !== "failed"}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onOpenReport) onOpenReport(run.id);
                        dispatch(setSelectedRunId(run.id));
                      }}
                      sx={{
                        backgroundColor: "rgba(59, 130, 246, 0.05)",
                        "&:hover": { backgroundColor: "rgba(59, 130, 246, 0.15)" }
                      }}
                    >
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {filteredRuns.length === 0 && (
              <TableRow>
                <TableCell colSpan={5}>
                  <Box sx={{ textAlign: "center", py: 3 }}>
                    <Typography variant="body2" color="text.secondary">
                      {runs.length === 0
                        ? "No analysis runs yet. Create a new analysis to get started."
                        : "No runs match your search criteria. Try adjusting your filters."}
                    </Typography>
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Results count */}
      {runs.length > 0 && (
        <Box sx={{ mt: 1.5, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Typography variant="caption" color="text.secondary">
            Showing {filteredRuns.length} of {runs.length} runs
          </Typography>
        </Box>
      )}
    </Paper>
  );
};
