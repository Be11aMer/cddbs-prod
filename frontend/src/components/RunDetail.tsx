import {
  Box,
  Paper,
  Typography,
  Divider,
  Chip,
  Stack,
  Link as MuiLink,
  CircularProgress,
  Alert,
  Button,
} from "@mui/material";
import ArticleIcon from "@mui/icons-material/Article";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DownloadIcon from "@mui/icons-material/Download";
import { useQuery } from "@tanstack/react-query";
import { fetchRun } from "../api";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useNotification } from "../contexts/NotificationContext";
import { DetailSkeleton } from "./Skeletons";

interface Props {
  runId: number | null;
  onOpenReport?: (id: number) => void;
}

export const RunDetail = ({ runId, onOpenReport }: Props) => {
  const { showSuccess, showError } = useNotification();

  const { data, isLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => fetchRun(runId as number),
    enabled: runId !== null,
    refetchInterval: (query) => {
      // Auto-refresh every 3 seconds if report is not complete
      const data = query.state.data;
      return data && !data.final_report ? 3000 : false;
    },
  });

  const handleCopyToClipboard = async () => {
    if (!data?.final_report) return;

    try {
      await navigator.clipboard.writeText(data.final_report);
      showSuccess("Briefing copied to clipboard!");
    } catch (error) {
      showError("Failed to copy to clipboard");
    }
  };

  const handleDownloadMarkdown = () => {
    if (!data?.final_report) return;

    const blob = new Blob([data.final_report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `briefing-${data.outlet}-${data.id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showSuccess("Briefing downloaded as Markdown!");
  };

  if (isLoading) {
    return <DetailSkeleton />;
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
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6" fontWeight={600}>
          Briefing Detail
        </Typography>
        {data?.final_report && (
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              startIcon={<ContentCopyIcon fontSize="small" />}
              onClick={handleCopyToClipboard}
              sx={{ textTransform: "none" }}
            >
              Copy
            </Button>
            <Button
              size="small"
              startIcon={<DownloadIcon fontSize="small" />}
              onClick={handleDownloadMarkdown}
              sx={{ textTransform: "none" }}
            >
              Download
            </Button>
          </Stack>
        )}
      </Box>
      {runId === null ? (
        <Box
          sx={{
            flexGrow: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
          }}
        >
          <ArticleIcon
            sx={{
              fontSize: 64,
              color: "text.disabled",
              mb: 2,
              opacity: 0.5,
            }}
          />
          <Typography variant="h6" gutterBottom>
            No Briefing Selected
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Select an analysis run from the table to view its intelligence
            briefing
          </Typography>
        </Box>
      ) : (
        data && (
          <Box sx={{ mt: 1, flexGrow: 1, overflow: "auto", pr: 1 }}>
            <Box sx={{ mb: 3 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, display: "block", mb: 0.5 }}>
                Outlet
              </Typography>
              <Typography variant="body1" fontWeight={600}>
                {data.outlet} {data.country ? `(${data.country})` : ""}
              </Typography>

              {data.meta?.url && (
                <Box sx={{ mt: 1.5 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, display: "block", mb: 0.5 }}>
                    Source URL
                  </Typography>
                  <MuiLink
                    href={data.meta.url}
                    target="_blank"
                    rel="noreferrer"
                    underline="hover"
                    sx={{ fontSize: "0.875rem", wordBreak: "break-all" }}
                  >
                    {data.meta.url}
                  </MuiLink>
                </Box>
              )}
            </Box>

            <Divider sx={{ my: 2, opacity: 0.5 }} />

            {data.articles.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, display: "block", mb: 1.5 }}>
                  Articles Analyzed ({data.meta?.articles_analyzed || data.articles.length})
                </Typography>
                <Stack spacing={1.5}>
                  {data.articles.slice(0, 5).map((article) => (
                    <Box key={article.id} sx={{ p: 1.5, borderRadius: 2, backgroundColor: "rgba(148, 163, 184, 0.05)", border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                      <Typography variant="body2" fontWeight={600} gutterBottom>
                        {article.title}
                      </Typography>
                      {article.link && (
                        <MuiLink
                          href={article.link}
                          target="_blank"
                          rel="noreferrer"
                          variant="caption"
                          underline="hover"
                          color="primary"
                          sx={{ display: "block", wordBreak: "break-all" }}
                        >
                          {article.link}
                        </MuiLink>
                      )}
                    </Box>
                  ))}
                  {data.articles.length > 5 && (
                    <Chip
                      size="small"
                      label={`+${data.articles.length - 5} more articles`}
                      variant="outlined"
                      sx={{ alignSelf: "flex-start", borderRadius: 1 }}
                    />
                  )}
                </Stack>
              </Box>
            )}

            <Divider sx={{ my: 2, opacity: 0.5 }} />

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, display: "block", mb: 1.5 }}>
                Status Summary
              </Typography>

              <Alert
                severity={data.status === "failed" ? "error" : (data.final_report ? "success" : "info")}
                sx={{
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: data.status === "failed" ? "error.light" : (data.final_report ? "success.light" : "info.light")
                }}
              >
                {data.status === "failed"
                  ? `Analysis Failed: ${data.message || "Unknown error"}`
                  : (data.final_report ? "Analysis complete. Detailed intelligence briefing is ready for review." : "Analysis in progress. Fetching and analyzing narratives...")
                }
              </Alert>

              <Button
                fullWidth
                variant="contained"
                onClick={() => onOpenReport?.(data.id)}
                disabled={data.status !== "completed" && data.status !== "failed"}
                sx={{
                  mt: 3,
                  borderRadius: 2,
                  py: 1.2,
                  textTransform: "none",
                  fontWeight: 700,
                  boxShadow: "0 4px 12px rgba(59, 130, 246, 0.25)"
                }}
              >
                Open Briefing Details
              </Button>
            </Box>
          </Box>
        )
      )}
    </Paper>
  );
};
