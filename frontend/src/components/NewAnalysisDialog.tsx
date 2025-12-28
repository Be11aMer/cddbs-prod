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
} from "@mui/material";
import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CreateRunPayload, createAnalysisRun, fetchApiStatus } from "../api";
import { ApiStatusInfo } from "./ApiStatusInfo";
import { useNotification } from "../contexts/NotificationContext";
import { getErrorMessage } from "../utils/errorMessages";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export const NewAnalysisDialog = ({ open, onClose, onCreated }: Props) => {
  const [form, setForm] = useState<CreateRunPayload>({
    outlet: "RT",
    url: "rt.com",
    country: "Russia",
    num_articles: 5,
  });
  const [showApiStatus, setShowApiStatus] = useState(false);
  const { showSuccess, showError } = useNotification();

  const { data: apiStatus, refetch: refetchApiStatus } = useQuery({
    queryKey: ["api-status"],
    queryFn: fetchApiStatus,
    enabled: false, // Don't auto-fetch - only fetch when explicitly requested
  });

  const mutation = useMutation({
    mutationFn: createAnalysisRun,
    onSuccess: () => {
      showSuccess("Analysis started successfully! Check the runs table for progress.");
      onCreated();
    },
    onError: (error) => {
      showError(getErrorMessage(error));
    },
  });

  // When dialog opens, fetch API status once and show info panel
  useEffect(() => {
    if (open) {
      refetchApiStatus().then(() => {
        setShowApiStatus(true);
        // Auto-hide after 8 seconds
        const timer = setTimeout(() => {
          setShowApiStatus(false);
        }, 8000);
        return () => clearTimeout(timer);
      });
    } else {
      setShowApiStatus(false);
    }
  }, [open, refetchApiStatus]);

  const handleChange = (field: keyof CreateRunPayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>New Analysis</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          {showApiStatus && apiStatus && (
            <ApiStatusInfo status={apiStatus} onClose={() => setShowApiStatus(false)} />
          )}
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Outlet"
                fullWidth
                value={form.outlet}
                onChange={(e) => handleChange("outlet", e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Domain"
                fullWidth
                value={form.url}
                onChange={(e) => handleChange("url", e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Country / Region"
                fullWidth
                value={form.country}
                onChange={(e) => handleChange("country", e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Articles"
                type="number"
                inputProps={{ min: 1, max: 20 }}
                fullWidth
                value={form.num_articles}
                onChange={(e) =>
                  handleChange("num_articles", e.target.value || "5")
                }
              />
            </Grid>
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={() => mutation.mutate(form)}
          disabled={mutation.isPending}
          startIcon={mutation.isPending ? <CircularProgress size={16} /> : undefined}
        >
          {mutation.isPending ? "Starting..." : "Run Analysis"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
