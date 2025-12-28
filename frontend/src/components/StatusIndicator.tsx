import {
  Box,
  Chip,
  Paper,
  Typography,
  Stack,
  CircularProgress,
  Tooltip,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import WarningIcon from "@mui/icons-material/Warning";
import { useQuery } from "@tanstack/react-query";
import { fetchApiStatus } from "../api";

export const StatusIndicator = () => {
  const { data: status, isLoading } = useQuery({
    queryKey: ["api-status"],
    queryFn: fetchApiStatus,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <Paper
        sx={{
          p: 1.5,
          border: "1px solid rgba(148,163,184,0.35)",
          backgroundColor: "rgba(15,23,42,0.5)",
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          <CircularProgress size={16} />
          <Typography variant="caption" color="text.secondary">
            Checking API status...
          </Typography>
        </Stack>
      </Paper>
    );
  }

  if (!status) return null;

  const getStatusIcon = (
    apiStatus: "configured" | "not_configured" | "ok" | "error" | "timeout" | "unknown"
  ) => {
    switch (apiStatus) {
      case "ok":
      case "configured":
        return <CheckCircleIcon sx={{ fontSize: 16, color: "#22c55e" }} />;
      case "error":
      case "timeout":
        return <ErrorIcon sx={{ fontSize: 16, color: "#ef4444" }} />;
      case "not_configured":
        return <WarningIcon sx={{ fontSize: 16, color: "#f59e0b" }} />;
      default:
        return <WarningIcon sx={{ fontSize: 16, color: "#94a3b8" }} />;
    }
  };

  const getStatusColor = (
    apiStatus: "configured" | "not_configured" | "ok" | "error" | "timeout" | "unknown"
  ): "success" | "error" | "warning" | "default" => {
    switch (apiStatus) {
      case "ok":
      case "configured":
        return "success";
      case "error":
      case "timeout":
        return "error";
      case "not_configured":
        return "warning";
      default:
        return "default";
    }
  };

  return (
    <Paper
      sx={{
        p: 1.5,
        border: "1px solid rgba(148,163,184,0.35)",
        backgroundColor: "rgba(15,23,42,0.5)",
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
        API Status
      </Typography>
      <Stack direction="row" spacing={1.5} alignItems="center">
        <Tooltip title={status.serpapi.message || "SerpAPI status"}>
          <Chip
            icon={getStatusIcon(status.serpapi.status)}
            label="SerpAPI"
            size="small"
            color={getStatusColor(status.serpapi.status)}
            variant="outlined"
            sx={{ height: 24 }}
          />
        </Tooltip>
        <Tooltip title={status.gemini.message || "Gemini API status"}>
          <Chip
            icon={getStatusIcon(status.gemini.status)}
            label="Gemini"
            size="small"
            color={getStatusColor(status.gemini.status)}
            variant="outlined"
            sx={{ height: 24 }}
          />
        </Tooltip>
      </Stack>
    </Paper>
  );
};

