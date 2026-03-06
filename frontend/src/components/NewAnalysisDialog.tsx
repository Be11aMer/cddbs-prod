import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Grid,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  Divider,
} from "@mui/material";
import NewspaperIcon from "@mui/icons-material/Newspaper";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CreateRunPayload,
  CreateTopicRunPayload,
  createAnalysisRun,
  createTopicRun,
  fetchApiStatus,
} from "../api";
import { ApiStatusInfo } from "./ApiStatusInfo";
import { useNotification } from "../contexts/NotificationContext";
import { getErrorMessage } from "../utils/errorMessages";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (mode: "outlet" | "topic") => void;
}

type Mode = "outlet" | "topic";

export const NewAnalysisDialog = ({ open, onClose, onCreated }: Props) => {
  const [mode, setMode] = useState<Mode>("outlet");

  const [outletForm, setOutletForm] = useState<CreateRunPayload>({
    outlet: "RT",
    url: "rt.com",
    country: "Russia",
    num_articles: 5,
    date_filter: "m",
  });

  const [topicForm, setTopicForm] = useState<CreateTopicRunPayload>({
    topic: "",
    num_outlets: 5,
    date_filter: "m",
  });

  const [showApiStatus, setShowApiStatus] = useState(false);
  const { showSuccess, showError } = useNotification();

  const { data: apiStatus, refetch: refetchApiStatus } = useQuery({
    queryKey: ["api-status"],
    queryFn: fetchApiStatus,
    enabled: false,
  });

  const outletMutation = useMutation({
    mutationFn: (payload: CreateRunPayload) => {
      const serpapiKey = localStorage.getItem("SERPAPI_KEY");
      const googleApiKey = localStorage.getItem("GOOGLE_API_KEY");
      return createAnalysisRun({
        ...payload,
        serpapi_key: serpapiKey || undefined,
        google_api_key: googleApiKey || undefined,
      });
    },
    onSuccess: () => {
      showSuccess("Analysis started successfully! Check the runs table for progress.");
      onCreated("outlet");
    },
    onError: (error) => {
      showError(getErrorMessage(error));
    },
  });

  const topicMutation = useMutation({
    mutationFn: (payload: CreateTopicRunPayload) => {
      const serpapiKey = localStorage.getItem("SERPAPI_KEY");
      const googleApiKey = localStorage.getItem("GOOGLE_API_KEY");
      return createTopicRun({
        ...payload,
        serpapi_key: serpapiKey || undefined,
        google_api_key: googleApiKey || undefined,
      });
    },
    onSuccess: () => {
      showSuccess("Topic analysis started! Results will appear as outlets are discovered.");
      onCreated("topic");
    },
    onError: (error) => {
      showError(getErrorMessage(error));
    },
  });

  useEffect(() => {
    if (open) {
      refetchApiStatus().then(() => {
        setShowApiStatus(true);
        const timer = setTimeout(() => setShowApiStatus(false), 8000);
        return () => clearTimeout(timer);
      });
    } else {
      setShowApiStatus(false);
    }
  }, [open, refetchApiStatus]);

  const isPending = outletMutation.isPending || topicMutation.isPending;

  const handleSubmit = () => {
    if (mode === "outlet") {
      outletMutation.mutate(outletForm);
    } else {
      topicMutation.mutate(topicForm);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>New Analysis</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          {/* Mode toggle */}
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={(_, val) => val && setMode(val)}
            size="small"
            fullWidth
            sx={{ mb: 2.5 }}
          >
            <ToggleButton value="outlet" sx={{ gap: 1, py: 1 }}>
              <NewspaperIcon fontSize="small" />
              <Box sx={{ textAlign: "left" }}>
                <Typography variant="caption" fontWeight={700} display="block" sx={{ lineHeight: 1.2 }}>
                  Outlet Mode
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem", lineHeight: 1.2 }}>
                  Analyse a specific outlet
                </Typography>
              </Box>
            </ToggleButton>
            <ToggleButton value="topic" sx={{ gap: 1, py: 1 }}>
              <TravelExploreIcon fontSize="small" />
              <Box sx={{ textAlign: "left" }}>
                <Typography variant="caption" fontWeight={700} display="block" sx={{ lineHeight: 1.2 }}>
                  Topic Mode
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem", lineHeight: 1.2 }}>
                  Discover who's pushing a narrative
                </Typography>
              </Box>
            </ToggleButton>
          </ToggleButtonGroup>

          <Divider sx={{ mb: 2 }} />

          {showApiStatus && apiStatus && (
            <ApiStatusInfo status={apiStatus} onClose={() => setShowApiStatus(false)} />
          )}

          {/* Outlet Mode form */}
          {mode === "outlet" && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Outlet"
                  fullWidth
                  value={outletForm.outlet}
                  onChange={(e) => setOutletForm((p) => ({ ...p, outlet: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Domain"
                  fullWidth
                  value={outletForm.url}
                  onChange={(e) => setOutletForm((p) => ({ ...p, url: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Country / Region"
                  fullWidth
                  value={outletForm.country}
                  onChange={(e) => setOutletForm((p) => ({ ...p, country: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Articles"
                  type="number"
                  inputProps={{ min: 1, max: 20 }}
                  fullWidth
                  value={outletForm.num_articles}
                  onChange={(e) =>
                    setOutletForm((p) => ({ ...p, num_articles: parseInt(e.target.value) || 5 }))
                  }
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <FormControl fullWidth>
                  <InputLabel>Time Period</InputLabel>
                  <Select
                    value={outletForm.date_filter || "m"}
                    label="Time Period"
                    onChange={(e) => setOutletForm((p) => ({ ...p, date_filter: e.target.value }))}
                  >
                    <MenuItem value="h">Past Hour</MenuItem>
                    <MenuItem value="d">Past Day</MenuItem>
                    <MenuItem value="w">Past Week</MenuItem>
                    <MenuItem value="m">Past Month</MenuItem>
                    <MenuItem value="y">Past Year</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          )}

          {/* Topic Mode form */}
          {mode === "topic" && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  label="Topic"
                  fullWidth
                  placeholder='e.g. "NATO expansion" or "COVID vaccine safety"'
                  value={topicForm.topic}
                  onChange={(e) => setTopicForm((p) => ({ ...p, topic: e.target.value }))}
                  helperText="The system will find neutral wire-service coverage as a baseline, then discover which outlets are using this topic to push narratives."
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Max Outlets to Analyse"
                  type="number"
                  inputProps={{ min: 1, max: 10 }}
                  fullWidth
                  value={topicForm.num_outlets}
                  onChange={(e) =>
                    setTopicForm((p) => ({ ...p, num_outlets: parseInt(e.target.value) || 5 }))
                  }
                  helperText="Top outlets by amplification frequency (1–10)"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Time Period</InputLabel>
                  <Select
                    value={topicForm.date_filter || "m"}
                    label="Time Period"
                    onChange={(e) => setTopicForm((p) => ({ ...p, date_filter: e.target.value }))}
                  >
                    <MenuItem value="h">Past Hour</MenuItem>
                    <MenuItem value="d">Past Day</MenuItem>
                    <MenuItem value="w">Past Week</MenuItem>
                    <MenuItem value="m">Past Month</MenuItem>
                    <MenuItem value="y">Past Year</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isPending || (mode === "topic" && !topicForm.topic.trim())}
          startIcon={isPending ? <CircularProgress size={16} /> : undefined}
        >
          {isPending
            ? "Starting..."
            : mode === "outlet"
            ? "Run Analysis"
            : "Start Topic Scan"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
