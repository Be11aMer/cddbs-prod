import {
  Alert,
  Box,
  IconButton,
  Stack,
  Typography,
  Chip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningIcon from "@mui/icons-material/Warning";
import { ApiStatus } from "../api";

interface Props {
  status: ApiStatus;
  onClose: () => void;
}

export const ApiStatusInfo = ({ status, onClose }: Props) => {
  // Check if APIs are configured (not making actual API calls to avoid token consumption)
  const serpapiOk = status.serpapi.configured && status.serpapi.status === "configured";
  const geminiOk = status.gemini.configured && status.gemini.status === "configured";
  const allOk = serpapiOk && geminiOk;

  const getStatusIcon = (configured: boolean) => {
    return configured ? (
      <CheckCircleIcon sx={{ fontSize: 16, color: "#22c55e" }} />
    ) : (
      <WarningIcon sx={{ fontSize: 16, color: "#f59e0b" }} />
    );
  };

  return (
    <Alert
      severity={allOk ? "success" : "warning"}
      onClose={onClose}
      action={
        <IconButton
          aria-label="close"
          color="inherit"
          size="small"
          onClick={onClose}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      }
      sx={{ mb: 2 }}
    >
      <Box>
        <Typography variant="body2" fontWeight={600} gutterBottom>
          API Configuration Status
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
          <Chip
            icon={getStatusIcon(serpapiOk)}
            label="SerpAPI"
            size="small"
            color={serpapiOk ? "success" : "warning"}
            variant="outlined"
            sx={{ height: 24 }}
          />
          <Chip
            icon={getStatusIcon(geminiOk)}
            label="Gemini"
            size="small"
            color={geminiOk ? "success" : "warning"}
            variant="outlined"
            sx={{ height: 24 }}
          />
        </Stack>
        {allOk ? (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
            Both APIs are configured. Analysis can proceed.
          </Typography>
        ) : (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
            {!serpapiOk && !geminiOk
              ? "Both API keys are missing. Please configure SERPAPI_KEY and GOOGLE_API_KEY in your .env file."
              : !serpapiOk
              ? "SerpAPI key is missing. Please configure SERPAPI_KEY in your .env file."
              : "Google API key is missing. Please configure GOOGLE_API_KEY in your .env file."}
          </Typography>
        )}
      </Box>
    </Alert>
  );
};
